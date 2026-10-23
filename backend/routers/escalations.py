"""
escalations.py — Escalation management router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import Article, ArticleChunk, AuditLog, Escalation, Session as SessionModel, User
from schemas import EscalationAssignRequest, EscalationOut, EscalationResolveRequest
from services.groq_service import get_embedding
from services.notification_service import send_escalation_assignment_alert
from services.jira_service import update_ticket_status
from os import getenv

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    return str(uuid.uuid4())


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


def _escalation_to_schema(e: Escalation) -> EscalationOut:
    def _load(val):
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    # Generate Jira URL if we have a reference
    jira_url = None
    if e.jira_reference:
        from services.jira_service import get_ticket_info
        ticket_info = get_ticket_info(e.jira_reference)
        if ticket_info:
            jira_url = ticket_info.get("url")
        else:
            # Fallback URL construction
            from os import getenv
            jira_url = f"{getenv('JIRA_URL', '')}/browse/{e.jira_reference}"

    return EscalationOut(
        id=e.id,
        session_id=e.session_id,
        original_query=e.original_query,
        matched_articles=_load(e.matched_articles),
        steps_attempted=_load(e.steps_attempted),
        actions_attempted=_load(e.actions_attempted),
        reason=e.reason,
        jira_reference=e.jira_reference,
        jira_url=jira_url,
        assigned_agent_id=e.assigned_agent_id,
        resolution_status=e.resolution_status,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /escalations
# ---------------------------------------------------------------------------

@router.get("", response_model=List[EscalationOut])
def list_escalations(
    resolution_status: Optional[str] = Query(None),
    db: DBSession = Depends(get_db),
):
    query = db.query(Escalation)
    if resolution_status:
        query = query.filter(Escalation.resolution_status == resolution_status)
    escalations = query.order_by(Escalation.created_at.desc()).all()
    return [_escalation_to_schema(e) for e in escalations]


# ---------------------------------------------------------------------------
# GET /escalations/{id}
# ---------------------------------------------------------------------------

@router.get("/{escalation_id}", response_model=EscalationOut)
def get_escalation(escalation_id: str, db: DBSession = Depends(get_db)):
    e = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _escalation_to_schema(e)


# ---------------------------------------------------------------------------
# PUT /escalations/{id}/assign
# ---------------------------------------------------------------------------

@router.put("/{escalation_id}/assign", response_model=EscalationOut)
def assign_escalation(
    escalation_id: str,
    payload: EscalationAssignRequest,
    db: DBSession = Depends(get_db),
):
    e = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Escalation not found")

    e.assigned_agent_id = payload.agent_id
    e.resolution_status = "in_progress"
    e.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "escalation_assigned",
        payload.agent_id,
        {"escalation_id": escalation_id, "agent_id": payload.agent_id},
    )

    # Trigger email alert
    agent = db.query(User).filter(User.id == payload.agent_id).first()
    if agent and e.jira_reference:
        jira_url = f"{getenv('JIRA_URL', '')}/browse/{e.jira_reference}"
        send_escalation_assignment_alert(
            agent_email=agent.email,
            agent_name=agent.name,
            jira_url=jira_url,
            original_query=e.original_query
        )

    return _escalation_to_schema(e)


# ---------------------------------------------------------------------------
# POST /escalations/{id}/resolve
# ---------------------------------------------------------------------------

@router.post("/{escalation_id}/resolve")
def resolve_escalation(
    escalation_id: str,
    payload: EscalationResolveRequest,
    db: DBSession = Depends(get_db),
):
    e = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Escalation not found")

    e.resolution_status = "resolved"
    e.updated_at = _utcnow()
    db.commit()

    # Update Jira ticket status
    jira_updated = update_ticket_status(
        e.jira_reference, 
        "Done", 
        f"Resolution: {payload.resolution_notes}"
    )
    
    if not jira_updated and e.jira_reference:
        log_audit(
            db,
            "jira_sync_failed",
            e.assigned_agent_id,
            {
                "escalation_id": escalation_id,
                "jira_reference": e.jira_reference,
                "action": "resolve",
                "error": "Failed to update Jira ticket status"
            },
        )

    # Close the related session
    session = db.query(SessionModel).filter(SessionModel.id == e.session_id).first()
    if session and session.status != "resolved":
        session.status = "resolved"
        session.closed_at = _utcnow()
        db.commit()

    # Optionally create a draft article from resolution
    new_article_id = None
    if payload.create_article and payload.article_title and payload.article_author_id:
        article = Article(
            id=_new_uuid(),
            title=payload.article_title,
            content=(
                f"Resolution for escalation {escalation_id}:\n\n"
                f"Original query: {e.original_query}\n\n"
                f"Resolution:\n{payload.resolution_notes}"
            ),
            author_id=payload.article_author_id,
            author_type="agent_drafted",
            lifecycle_status="draft",
            version=1,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        # Chunk the new article
        from routers.articles import _create_article_chunks
        _create_article_chunks(db, article)

        new_article_id = article.id

    log_audit(
        db,
        "escalation_resolved",
        e.assigned_agent_id,
        {
            "escalation_id": escalation_id,
            "resolution_notes": payload.resolution_notes,
            "draft_article_created": new_article_id,
            "jira_updated": jira_updated,
        },
    )

    result = _escalation_to_schema(e)
    if new_article_id:
        # Include draft article reference in response via extra field
        return {
            **result.model_dump(),
            "draft_article_id": new_article_id,
            "jira_updated": jira_updated,
        }
    return result


# ---------------------------------------------------------------------------
# POST /escalations/{id}/sync-jira
# ---------------------------------------------------------------------------

@router.post("/{escalation_id}/sync-jira")
def sync_jira_status(
    escalation_id: str,
    db: DBSession = Depends(get_db),
):
    """Manually sync escalation status with Jira."""
    e = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    if not e.jira_reference:
        raise HTTPException(status_code=400, detail="No Jira reference to sync")
    
    from services.jira_service import get_ticket_info
    ticket_info = get_ticket_info(e.jira_reference)
    
    if ticket_info:
        # Update local status based on Jira status
        jira_status = ticket_info.get("status", "").lower()
        if "done" in jira_status or "closed" in jira_status:
            e.resolution_status = "resolved"
        elif "in progress" in jira_status or "started" in jira_status:
            e.resolution_status = "in_progress"
        
        e.updated_at = _utcnow()
        db.commit()
        
        log_audit(
            db,
            "jira_status_synced",
            e.assigned_agent_id,
            {
                "escalation_id": escalation_id,
                "jira_reference": e.jira_reference,
                "jira_status": ticket_info.get("status"),
                "local_status": e.resolution_status
            },
        )
        
        return {
            "success": True,
            "jira_status": ticket_info.get("status"),
            "local_status": e.resolution_status,
            "synced": True
        }
    else:
        return {
            "success": False,
            "error": "Could not fetch Jira ticket info",
            "jira_reference": e.jira_reference
        }
