"""
chat.py — Main chat router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import (
    AccessRequest,
    AuditLog,
    Escalation,
    GuardrailBlock,
    Interaction,
    InteractionStep,
    FaithfulnessFailure,
    Resource,
    Session as SessionModel,
)
from schemas import (
    ChatRequest,
    ChatResponse,
    SatisfactionRating,
    SessionOut,
    StepResponseOut,
    StepResponseRequest,
)
from services import groq_service, rag_service
from services.rate_limit_service import check_rate_limit

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _is_conversational_opener(query: str) -> bool:
    text = re.sub(r"[^a-z0-9\s]", " ", query.lower()).strip()
    text = re.sub(r"\s+", " ", text)
    greetings = {
        "hi",
        "hello",
        "hey",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
        "ok",
        "okay",
    }
    return text in greetings


def _normalized_query(query: str) -> str:
    text = re.sub(r"[^a-z0-9\s]", " ", query.lower()).strip()
    return re.sub(r"\s+", " ", text)


def _is_step_followup(query: str) -> bool:
    text = _normalized_query(query)
    patterns = [
        r"\b(additional|more|next|remaining|other)\s+(step|steps|instruction|instructions)\b",
        r"\b(give|show|tell)\s+me\s+(the\s+)?(additional|more|next|remaining|other)\b",
        r"\bwhat\s+(else|next)\b",
        r"\bcontinue\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _is_affirmative(query: str) -> bool:
    return _normalized_query(query) in {"yes", "y", "yeah", "yep", "resolved", "fixed", "it worked", "done"}


def _is_negative(query: str) -> bool:
    return _normalized_query(query) in {"no", "n", "nope", "not resolved", "did not work", "didnt work", "still broken", "continue", "next"}


def _get_last_interaction(db: DBSession, session_id: str) -> Optional[Interaction]:
    return (
        db.query(Interaction)
        .filter(Interaction.session_id == session_id)
        .order_by(Interaction.timestamp.desc())
        .first()
    )


def _get_previous_article_with_steps(db: DBSession, session_id: str):
    from models import Article

    previous = (
        db.query(Interaction)
        .filter(Interaction.session_id == session_id)
        .filter(Interaction.matched_article_ids.isnot(None))
        .order_by(Interaction.timestamp.desc())
        .all()
    )
    for interaction in previous:
        try:
            article_ids = json.loads(interaction.matched_article_ids or "[]")
        except Exception:
            article_ids = []
        for article_id in article_ids:
            article = db.query(Article).filter(Article.id == article_id).first()
            if article and article.steps:
                try:
                    article_steps = json.loads(article.steps)
                except Exception:
                    article_steps = []
                if article_steps:
                    return article, article_steps
    return None, []


def _get_recent_context(db: DBSession, session_id: str) -> dict:
    last = _get_last_interaction(db, session_id)
    article, steps = _get_previous_article_with_steps(db, session_id)
    return {
        "last_intent": last.intent if last else None,
        "last_query": last.query_text if last else "",
        "last_response": last.response_text if last else "",
        "last_article_id": article.id if article else None,
        "last_article_title": article.title if article else "",
        "last_article_steps": steps,
    }


def _get_pending_access_state(db: DBSession, session_id: str) -> dict:
    previous = (
        db.query(Interaction)
        .filter(Interaction.session_id == session_id)
        .filter(Interaction.action_invocations.isnot(None))
        .order_by(Interaction.timestamp.desc())
        .all()
    )
    for interaction in previous:
        try:
            actions = json.loads(interaction.action_invocations or "[]")
        except Exception:
            actions = []
        for action in actions:
            if action.get("type") == "access_request_created":
                return {}
            if action.get("type") == "access_request_draft" and action.get("status") == "collecting":
                return action
    return {}


def _find_or_create_resource(db: DBSession, resource_name: str) -> Resource:
    normalized = resource_name.strip()
    existing = (
        db.query(Resource)
        .filter(Resource.name.ilike(normalized))
        .first()
    )
    if existing:
        return existing

    resource = Resource(
        id=_new_uuid(),
        name=normalized,
        category="Application",
        approval_cascade=json.dumps([{"type": "it_operations_review"}]),
        created_at=_utcnow(),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def _create_access_request_from_chat(
    db: DBSession,
    requester_id: str,
    resource_name: str,
    reason: str,
) -> AccessRequest:
    resource = _find_or_create_resource(db, resource_name)
    cascade = []
    if resource.approval_cascade:
        try:
            cascade = json.loads(resource.approval_cascade)
        except Exception:
            cascade = []
    request = AccessRequest(
        id=_new_uuid(),
        requester_id=requester_id,
        resource_id=resource.id,
        reason=reason,
        cascade_instance=json.dumps({
            "cascade": cascade,
            "current_level": 0,
            "total_levels": len(cascade),
            "status": "pending" if cascade else "auto_approved",
        }),
        approval_history=json.dumps([]),
        provisioning_outcome=None if cascade else "granted",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

def log_audit(
    db: DBSession,
    event_type: str,
    actor_id: Optional[str],
    event_details: dict,
    data_classification_tag: str = "Public",
) -> None:
    entry = AuditLog(
        id=_new_uuid(),
        event_type=event_type,
        actor_id=actor_id,
        event_details=json.dumps(event_details),
        data_classification_tag=data_classification_tag,
        timestamp=_utcnow(),
    )
    db.add(entry)
    db.commit()


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: DBSession = Depends(get_db)):
    """Main chat endpoint with full RAG + guardrails pipeline."""

    # 1. Rate limit check (BR-020)
    allowed, rate_msg = check_rate_limit(request.user_id, db)
    if not allowed:
        raise HTTPException(status_code=429, detail=rate_msg)

    # 2. Guardrail check (BR-017)
    blocked, block_reason = groq_service.check_guardrails(request.query)
    if blocked:
        gb = GuardrailBlock(
            id=_new_uuid(),
            user_id=request.user_id,
            blocked_query=request.query,
            matched_pattern="llm_classifier",
            block_reason=block_reason,
            timestamp=_utcnow(),
        )
        db.add(gb)
        db.commit()
        log_audit(
            db,
            "guardrail_block",
            request.user_id,
            {"query": request.query, "reason": block_reason},
            "Internal",
        )
        raise HTTPException(
            status_code=400,
            detail=f"Query blocked by safety guardrails: {block_reason}",
        )

    # 3. Prohibited response class check (BR-019)
    proh_blocked, proh_redirect = groq_service.check_prohibited_response(request.query)
    if proh_blocked:
        log_audit(
            db,
            "prohibited_response_block",
            request.user_id,
            {"query": request.query, "redirect": proh_redirect},
        )
        session_id = request.session_id or _new_uuid()
        interaction_id = _new_uuid()
        return ChatResponse(
            response=proh_redirect,
            confidence_band="NONE",
            session_id=session_id,
            interaction_id=interaction_id,
            escalated=False,
        )

    # 4. Get or create Session
    session: Optional[SessionModel] = None
    if request.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
        if session and session.status in ("resolved", "escalated"):
            session = None
    if session is None:
        session = SessionModel(
            id=_new_uuid(),
            user_id=request.user_id,
            status="active",
            created_at=_utcnow(),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    context = _get_recent_context(db, session.id)
    pending_access = _get_pending_access_state(db, session.id)

    # 5. Parse natural-language intent before retrieval so the user's wording
    # drives routing even when no article has been matched yet.
    intent_data = groq_service.parse_intent(request.query, context.get("last_article_title", ""))
    intent = intent_data.get("intent", "other")
    if intent_data.get("requires_human"):
        intent = "escalation"
    if pending_access and intent not in {"escalation", "troubleshooting"}:
        intent = "access_request"

    # 6. RAG search
    chunks, best_score, confidence_band = rag_service.search_knowledge_base(
        request.query, db, top_k=5
    )
    chunk_texts = [c["chunk_text"] for c in chunks]
    article_ids = list({c["article_id"] for c in chunks if c.get("article_id")})

    # Classify intent using top article title from chunk metadata
    top_article_title = ""
    if chunks:
        # Try to get article title from DB
        from models import Article
        top_art = db.query(Article).filter(Article.id == chunks[0].get("article_id")).first()
        if top_art:
            top_article_title = top_art.title

    if intent == "other" and confidence_band != "NONE" and top_article_title:
        intent = groq_service.classify_intent(request.query, top_article_title)

    # 7. Build response based on intent and confidence band
    response_text = ""
    escalated = False
    jira_reference: Optional[str] = None
    steps: Optional[list] = None
    faithfulness_outcome: Optional[bool] = None
    ask_relevance = False
    action_invocations: list = []

    if intent == "escalation":
        escalated = True
        response_text = (
            "I'll create a support ticket and escalate this to our IT team. "
            "An IT support agent will reach out to you shortly."
        )
        jira_reference = _create_escalation(
            db, session, request.query, article_ids, [], "user_requested_escalation"
        )
        session.status = "escalated"
        session.closed_at = _utcnow()
        db.commit()

    elif intent == "access_request":
        entities = intent_data.get("entities", {}) if isinstance(intent_data.get("entities"), dict) else {}
        resource_name = entities.get("system") or pending_access.get("resource_name") or ""
        reason = entities.get("business_reason") or pending_access.get("reason") or ""
        access_level = entities.get("access_level") or pending_access.get("access_level") or ""

        if pending_access and not reason and resource_name:
            normalized = _normalized_query(request.query)
            if normalized not in {"yes", "no", "ok", "okay"} and resource_name.lower() not in normalized:
                reason = request.query.strip()

        missing = []
        if not resource_name:
            missing.append("the system or resource name")
        if not reason:
            missing.append("the business reason")

        if missing:
            action_invocations = [{
                "type": "access_request_draft",
                "status": "collecting",
                "resource_name": resource_name,
                "access_level": access_level,
                "reason": reason,
            }]
            response_text = (
                "I can help create that access request. "
                f"Please provide {', and '.join(missing)}."
            )
        else:
            access_request = _create_access_request_from_chat(
                db,
                requester_id=request.user_id,
                resource_name=resource_name,
                reason=reason if not access_level else f"{reason} Requested access level: {access_level}.",
            )
            action_invocations = [{
                "type": "access_request_created",
                "status": "created",
                "request_id": access_request.id,
                "resource_name": resource_name,
                "access_level": access_level,
                "reason": reason,
            }]
            outcome = access_request.provisioning_outcome or "pending approval"
            response_text = (
                f"I created an access request for **{resource_name}**. "
                f"Request ID: `{access_request.id}`. Current status: {outcome}."
            )
        session.status = "active"
        db.commit()

    elif session.status == "troubleshooting" and (_is_affirmative(request.query) or _is_negative(request.query)):
        previous_article, article_steps = _get_previous_article_with_steps(db, session.id)
        confidence_band = "HIGH"
        if previous_article:
            article_ids = [previous_article.id]
        if _is_affirmative(request.query):
            response_text = "Great, I'm glad that resolved your issue. How would you rate your experience?"
            session.status = "resolved"
            session.closed_at = _utcnow()
            db.commit()
        elif previous_article and article_steps:
            last_step = (
                db.query(InteractionStep)
                .join(Interaction, InteractionStep.interaction_id == Interaction.id)
                .filter(Interaction.session_id == session.id)
                .order_by(InteractionStep.step_order.desc())
                .first()
            )
            next_index = (last_step.step_order + 1) if last_step else 1
            if next_index < len(article_steps):
                response_text = (
                    f"Let's try the next step from **{previous_article.title}**.\n\n"
                    f"**Step {next_index + 1}:** {article_steps[next_index]}\n\n"
                    "Did that resolve your issue?"
                )
                step_record = InteractionStep(
                    id=_new_uuid(),
                    interaction_id=_get_last_interaction(db, session.id).id,
                    step_order=next_index,
                    step_content=article_steps[next_index],
                    step_timestamp=_utcnow(),
                )
                db.add(step_record)
                db.commit()
            else:
                escalated = True
                response_text = (
                    "We have tried all available troubleshooting steps. "
                    "I'll escalate this to IT support so a human can help."
                )
                jira_reference = _create_escalation(
                    db, session, context.get("last_query") or request.query, [previous_article.id], article_steps, "all_steps_exhausted"
                )
                session.status = "escalated"
                session.closed_at = _utcnow()
                db.commit()
        else:
            response_text = "I lost the troubleshooting context. Could you briefly describe the issue again?"
            session.status = "active"
            db.commit()

    elif _is_step_followup(request.query):
        previous_article, article_steps = _get_previous_article_with_steps(db, session.id)
        if previous_article and article_steps:
            remaining_steps = article_steps[3:] if len(article_steps) > 3 else article_steps
            steps = remaining_steps
            article_ids = [previous_article.id]
            top_article_title = previous_article.title
            confidence_band = "HIGH"
            response_text = (
                f"Here are the additional steps from **{previous_article.title}**:\n\n"
                + "\n".join(
                    f"{idx}. {step}"
                    for idx, step in enumerate(
                        remaining_steps,
                        start=(4 if len(article_steps) > 3 else 1),
                    )
                )
            )
            session.status = "active"
            db.commit()
        else:
            response_text = (
                "I can share additional steps once I know which issue we're working on. "
                "Could you mention the system or problem, such as Wi-Fi, VPN, laptop power, or password reset?"
            )
            session.status = "active"
            db.commit()

    elif confidence_band == "HIGH":
        if intent == "troubleshooting" and top_article_title:
            # Get steps from the matched article
            from models import Article as ArticleModel
            article = db.query(ArticleModel).filter(
                ArticleModel.id == chunks[0].get("article_id")
            ).first()

            if article and article.steps:
                try:
                    article_steps = json.loads(article.steps)
                except Exception:
                    article_steps = []
            else:
                article_steps = []

            if article_steps:
                steps = article_steps
                response_text = (
                    f"I found a troubleshooting guide for your issue: **{top_article_title}**\n\n"
                    f"Let's work through this step by step.\n\n"
                    f"**Step 1:** {article_steps[0]}\n\n"
                    f"Did that resolve your issue?"
                )
                session.status = "troubleshooting"
                db.commit()
            else:
                # No steps — fall through to FAQ answer
                answer = groq_service.generate_answer(request.query, chunk_texts)
                passed, claims = groq_service.check_faithfulness(answer, chunk_texts)
                faithfulness_outcome = passed
                if not passed:
                    escalated = True
                    response_text = (
                        "I found information but couldn't verify the accuracy of my answer. "
                        "I'm escalating this to our IT support team for a reliable response."
                    )
                    jira_reference = _create_escalation(
                        db, session, request.query, article_ids, [], "faithfulness_failure"
                    )
                    session.status = "escalated"
                    session.closed_at = _utcnow()
                    _store_faithfulness_failure(
                        db, None, request.query, answer, claims, chunk_texts
                    )
                else:
                    response_text = answer
                    session.status = "active"
                db.commit()
        else:
            # FAQ intent
            answer = groq_service.generate_answer(request.query, chunk_texts)
            passed, claims = groq_service.check_faithfulness(answer, chunk_texts)
            faithfulness_outcome = passed
            if not passed:
                escalated = True
                response_text = (
                    "I found relevant information but couldn't verify the accuracy of my answer. "
                    "I'm escalating this to our IT support team."
                )
                jira_reference = _create_escalation(
                    db, session, request.query, article_ids, [], "faithfulness_failure"
                )
                session.status = "escalated"
                session.closed_at = _utcnow()
                _store_faithfulness_failure(
                    db, None, request.query, answer, claims, chunk_texts
                )
            else:
                response_text = answer
                session.status = "active"
            db.commit()

    elif confidence_band == "LOW":
        # Return best match with relevance question
        if chunk_texts:
            response_text = (
                f"I found a potentially relevant article: **{top_article_title}**\n\n"
                f"{chunk_texts[0][:500]}{'...' if len(chunk_texts[0]) > 500 else ''}\n\n"
                f"Is this relevant to your question?"
            )
        else:
            response_text = "I found some partial information but I'm not confident it matches your query. Could you rephrase or provide more details?"
        ask_relevance = True
        session.status = "active"
        db.commit()

    elif intent == "other" and _is_conversational_opener(request.query):
        response_text = (
            "Hi! I can help with IT issues, access requests, troubleshooting, "
            "or creating a support ticket. What do you need help with?"
        )
        session.status = "active"
        db.commit()

    elif intent == "other":
        response_text = (
            "I can help with IT support questions, troubleshooting, access requests, "
            "or escalating to a human. Could you tell me what IT issue you need help with?"
        )
        session.status = "active"
        db.commit()

    else:  # NONE / low-information known intent
        response_text = (
            "I couldn't find an exact match in my knowledge base. "
            "Is this about Wi-Fi, VPN, password reset, software installation, laptop hardware, or an access request?"
        )
        ask_relevance = True
        session.status = "active"
        db.commit()

    # 8. Log Interaction
    interaction = Interaction(
        id=_new_uuid(),
        session_id=session.id,
        user_id=request.user_id,
        channel="web_chat",
        query_text=request.query,
        intent=intent,
        matched_article_ids=json.dumps(article_ids),
        confidence_band=confidence_band,
        response_text=response_text,
        steps_presented=json.dumps(steps) if steps else json.dumps([]),
        action_invocations=json.dumps(action_invocations),
        escalation_flag=escalated,
        jira_reference=jira_reference,
        faithfulness_outcome=faithfulness_outcome,
        adversarial_flag=False,
        timestamp=_utcnow(),
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    # If troubleshooting, store first step as InteractionStep
    if steps and confidence_band == "HIGH" and intent == "troubleshooting":
        step_record = InteractionStep(
            id=_new_uuid(),
            interaction_id=interaction.id,
            step_order=0,
            step_content=steps[0],
            step_timestamp=_utcnow(),
        )
        db.add(step_record)
        db.commit()

    # Update faithfulness failure with interaction_id if needed
    if faithfulness_outcome is False:
        ff = (
            db.query(FaithfulnessFailure)
            .filter(
                FaithfulnessFailure.original_query == request.query,
                FaithfulnessFailure.interaction_id == None,
            )
            .order_by(FaithfulnessFailure.timestamp.desc())
            .first()
        )
        if ff:
            ff.interaction_id = interaction.id
            db.commit()

    # 9. Audit log
    log_audit(
        db,
        "chat_interaction",
        request.user_id,
        {
            "interaction_id": interaction.id,
            "session_id": session.id,
            "confidence_band": confidence_band,
            "escalated": escalated,
            "intent": intent,
        },
    )

    return ChatResponse(
        response=response_text,
        confidence_band=confidence_band,
        session_id=session.id,
        interaction_id=interaction.id,
        escalated=escalated,
        jira_reference=jira_reference,
        steps=steps,
        ask_relevance=ask_relevance,
    )


# ---------------------------------------------------------------------------
# POST /chat/step-response
# ---------------------------------------------------------------------------

@router.post("/step-response", response_model=StepResponseOut)
def step_response(request: StepResponseRequest, db: DBSession = Depends(get_db)):
    """Handle user's yes/no response during multi-step troubleshooting."""

    session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    interaction = (
        db.query(Interaction).filter(Interaction.id == request.interaction_id).first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    # Load steps from the interaction
    try:
        steps = json.loads(interaction.steps_presented or "[]")
    except Exception:
        steps = []

    if request.resolved:
        # User confirmed resolved
        session.status = "resolved"
        session.closed_at = _utcnow()
        session.closed_at = _utcnow()
        db.commit()

        # Record user response on the step
        existing_step = (
            db.query(InteractionStep)
            .filter(
                InteractionStep.interaction_id == request.interaction_id,
                InteractionStep.step_order == request.step_index,
            )
            .first()
        )
        if existing_step:
            existing_step.user_response = "resolved"
            db.commit()

        log_audit(
            db,
            "session_resolved",
            session.user_id,
            {"session_id": session.id, "at_step": request.step_index},
        )

        return StepResponseOut(
            message="Great! I'm glad that resolved your issue. How would you rate your experience?",
            session_status="resolved",
            prompt_rating=True,
        )

    # Not resolved — try next step
    next_step_index = request.step_index + 1

    # Record user response
    existing_step = (
        db.query(InteractionStep)
        .filter(
            InteractionStep.interaction_id == request.interaction_id,
            InteractionStep.step_order == request.step_index,
        )
        .first()
    )
    if existing_step:
        existing_step.user_response = "not_resolved"
        db.commit()

    if next_step_index < len(steps):
        # Present next step
        next_content = steps[next_step_index]
        step_record = InteractionStep(
            id=_new_uuid(),
            interaction_id=interaction.id,
            step_order=next_step_index,
            step_content=next_content,
            step_timestamp=_utcnow(),
        )
        db.add(step_record)
        db.commit()

        log_audit(
            db,
            "troubleshooting_step_advance",
            session.user_id,
            {
                "session_id": session.id,
                "interaction_id": interaction.id,
                "step": next_step_index,
            },
        )

        return StepResponseOut(
            message=f"Let's try the next step.",
            next_step=next_content,
            step_index=next_step_index,
            session_status="troubleshooting",
        )

    # All steps exhausted — escalate
    matched_articles = json.loads(interaction.matched_article_ids or "[]")
    steps_tried = [s.step_content for s in interaction.steps]

    jira_ref = _create_escalation(
        db,
        session,
        interaction.query_text,
        matched_articles,
        steps_tried,
        "all_steps_exhausted",
    )

    interaction.escalation_flag = True
    interaction.jira_reference = jira_ref
    session.status = "escalated"
    session.closed_at = _utcnow()
    session.closed_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "escalation_after_troubleshooting",
        session.user_id,
        {"session_id": session.id, "jira_reference": jira_ref},
    )

    return StepResponseOut(
        message=(
            "I'm sorry the troubleshooting steps didn't resolve your issue. "
            f"I've escalated this to our IT support team (Reference: {jira_ref}). "
            "An agent will be in touch shortly."
        ),
        session_status="escalated",
        escalated=True,
        jira_reference=jira_ref,
    )


# ---------------------------------------------------------------------------
# POST /chat/rate
# ---------------------------------------------------------------------------

@router.post("/rate/{interaction_id}")
def rate_interaction(
    interaction_id: str,
    rating: SatisfactionRating,
    db: DBSession = Depends(get_db),
):
    """Submit satisfaction rating (1-5) for an interaction."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction.satisfaction_rating = rating.rating
    db.commit()

    log_audit(
        db,
        "satisfaction_rating_submitted",
        interaction.user_id,
        {"interaction_id": interaction_id, "rating": rating.rating},
    )

    return {"message": "Rating recorded. Thank you for your feedback!", "rating": rating.rating}


# ---------------------------------------------------------------------------
# GET /chat/session/{session_id}
# ---------------------------------------------------------------------------

@router.get("/session/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    """Get session state."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_escalation(
    db: DBSession,
    session: SessionModel,
    query: str,
    matched_article_ids: list,
    steps_tried: list,
    reason: str,
) -> str:
    """Create an Escalation record and real Jira ticket."""
    from services.jira_service import create_ticket
    
    # Prepare ticket description with chat context
    description = f"""*Escalated from Leila IT Help Desk Chat*

*Original Query:*
{query}

*Reason for Escalation:*
{reason}

*Matched Articles:*
{json.dumps(matched_article_ids, indent=2) if matched_article_ids else 'None'}

*Steps Attempted:*
{json.dumps(steps_tried, indent=2) if steps_tried else 'None'}

*Session ID:*
{session.id}

---
This ticket was automatically created when the AI assistant could not resolve the user's query."""
    
    # Create Jira ticket
    jira_result = create_ticket(
        summary=f"IT Support Escalation - {query[:50]}{'...' if len(query) > 50 else ''}",
        description=description,
        issue_type="Story",
        priority="Medium",
        labels=["escalated", "leila-chat", reason]
    )
    
    # Get the actual Jira reference
    jira_ref = jira_result.get("key", f"ESC-{_new_uuid()[:8].upper()}")
    
    # Send alert email
    from services.notification_service import send_new_escalation_alert
    import os
    jira_url = f"{os.getenv('JIRA_URL', '')}/browse/{jira_ref}"
    send_new_escalation_alert(jira_url, query)

    # Store escalation in local database
    escalation = Escalation(
        id=_new_uuid(),
        session_id=session.id,
        original_query=query,
        matched_articles=json.dumps(matched_article_ids),
        steps_attempted=json.dumps(steps_tried),
        actions_attempted=json.dumps([]),
        reason=reason,
        jira_reference=jira_ref,
        resolution_status="open",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(escalation)
    db.commit()
    
    return jira_ref


def _store_faithfulness_failure(
    db: DBSession,
    interaction_id: Optional[str],
    query: str,
    answer: str,
    claims: list,
    chunks: list,
) -> None:
    """Store a FaithfulnessFailure record."""
    ff = FaithfulnessFailure(
        id=_new_uuid(),
        interaction_id=interaction_id,
        original_query=query,
        llm_answer=answer,
        unsupported_claims=json.dumps(
            [c for c in claims if c.get("score", 1) < 0.85]
        ),
        retrieved_chunks=json.dumps(chunks[:5]),
        timestamp=_utcnow(),
    )
    db.add(ff)
    db.commit()


# ---------------------------------------------------------------------------
# GET /chat/history/{user_id}
# ---------------------------------------------------------------------------

@router.get("/history/{user_id}")
def get_chat_history(user_id: str, db: DBSession = Depends(get_db)):
    """Returns the chat history for a given user, ordered by timestamp."""
    interactions = (
        db.query(Interaction)
        .filter(Interaction.user_id == user_id)
        .order_by(Interaction.timestamp.asc())
        .all()
    )
    
    history = []
    for i in interactions:
        # User message
        history.append({
            "id": f"u-{i.id}",
            "role": "user",
            "content": i.query_text,
            "timestamp": i.timestamp.isoformat() + "Z",
        })
        
        # Assistant message
        if i.response_text:
            meta = {
                "interaction_id": i.id,
                "session_id": i.session_id,
                "escalated": i.escalation_flag,
                "jira_reference": i.jira_reference,
            }
            history.append({
                "id": f"a-{i.id}",
                "role": "assistant",
                "content": i.response_text,
                "timestamp": i.timestamp.isoformat() + "Z",
                "type": "escalation" if i.escalation_flag else "answer",
                "meta": meta
            })
            
    return {"messages": history}


# ---------------------------------------------------------------------------
# GET /chat/sessions/{user_id}
# ---------------------------------------------------------------------------

@router.get("/sessions/{user_id}")
def get_user_sessions(user_id: str, db: DBSession = Depends(get_db)):
    """Returns all chat sessions for a user, grouped with first query as title."""
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.desc())
        .all()
    )
    
    result = []
    for s in sessions:
        # Get the first interaction to use as a title
        first_interaction = (
            db.query(Interaction)
            .filter(Interaction.session_id == s.id)
            .order_by(Interaction.timestamp.asc())
            .first()
        )
        title = first_interaction.query_text if first_interaction else "New Chat"
        result.append({
            "id": s.id,
            "title": title[:50] + ("..." if len(title) > 50 else ""),
            "status": s.status,
            "created_at": s.created_at.isoformat() + "Z",
        })
    return result


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id}/history
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/history")
def get_session_history(session_id: str, db: DBSession = Depends(get_db)):
    """Returns the interaction history for a specific session."""
    interactions = (
        db.query(Interaction)
        .filter(Interaction.session_id == session_id)
        .order_by(Interaction.timestamp.asc())
        .all()
    )
    
    history = []
    for i in interactions:
        history.append({
            "id": f"u-{i.id}",
            "role": "user",
            "content": i.query_text,
            "timestamp": i.timestamp.isoformat() + "Z",
        })
        
        if i.response_text:
            meta = {
                "interaction_id": i.id,
                "session_id": i.session_id,
                "escalated": i.escalation_flag,
                "jira_reference": i.jira_reference,
            }
            history.append({
                "id": f"a-{i.id}",
                "role": "assistant",
                "content": i.response_text,
                "timestamp": i.timestamp.isoformat() + "Z",
                "type": "escalation" if i.escalation_flag else "answer",
                "meta": meta
            })
            
    return {"messages": history}
