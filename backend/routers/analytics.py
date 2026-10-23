"""
analytics.py — Analytics and reporting router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import (
    AccessRequest,
    AuditLog,
    Escalation,
    FaithfulnessFailure,
    GuardrailBlock,
    Interaction,
    Session as SessionModel,
)
from schemas import AnalyticsMetrics

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# GET /analytics/metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=AnalyticsMetrics)
def get_metrics(db: DBSession = Depends(get_db)):
    """Compute and return all 10 Arjuna operational metrics from the database."""

    total_interactions = db.query(func.count(Interaction.id)).scalar() or 0

    # 1. Query resolution rate — sessions resolved / total sessions closed
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    resolved_sessions = (
        db.query(func.count(SessionModel.id))
        .filter(SessionModel.status == "resolved")
        .scalar()
        or 0
    )
    query_resolution_rate = (
        resolved_sessions / total_sessions if total_sessions > 0 else 0.0
    )

    # 2. Escalation rate — interactions where escalation_flag=True / total
    escalated_count = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.escalation_flag == True)
        .scalar()
        or 0
    )
    escalation_rate = (
        escalated_count / total_interactions if total_interactions > 0 else 0.0
    )

    # 3. KB coverage rate — HIGH + LOW confidence / total (non-NONE)
    high_confidence = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.confidence_band == "HIGH")
        .scalar()
        or 0
    )
    low_confidence = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.confidence_band == "LOW")
        .scalar()
        or 0
    )
    kb_coverage_rate = (
        (high_confidence + low_confidence) / total_interactions
        if total_interactions > 0
        else 0.0
    )

    # 4. Model correction rate — faithfulness failures / total interactions with answer
    ff_count = db.query(func.count(FaithfulnessFailure.id)).scalar() or 0
    interactions_with_answer = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.response_text != None)
        .scalar()
        or 0
    )
    model_correction_rate = (
        ff_count / interactions_with_answer if interactions_with_answer > 0 else 0.0
    )

    # 5. Author correction rate — articles rejected / articles submitted
    total_audit_rejections = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.event_type == "article_rejected")
        .scalar()
        or 0
    )
    total_audit_submissions = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.event_type == "article_submitted_for_review")
        .scalar()
        or 0
    )
    author_correction_rate = (
        total_audit_rejections / total_audit_submissions
        if total_audit_submissions > 0
        else 0.0
    )

    # 6. Action success rate — currently no action framework, return 1.0 as default
    action_invocation_count = 0
    action_success_count = 0
    for interaction in db.query(Interaction).all():
        try:
            invocations = json.loads(interaction.action_invocations or "[]")
            for inv in invocations:
                action_invocation_count += 1
                if inv.get("outcome") == "success":
                    action_success_count += 1
        except Exception:
            pass
    action_success_rate = (
        action_success_count / action_invocation_count
        if action_invocation_count > 0
        else 1.0
    )

    # 7. Eligibility block rate — guardrail blocks / total query attempts
    guardrail_blocks = db.query(func.count(GuardrailBlock.id)).scalar() or 0
    total_queries = total_interactions + guardrail_blocks
    eligibility_block_rate = (
        guardrail_blocks / total_queries if total_queries > 0 else 0.0
    )

    # 8. Access request turnaround — average hours from created to updated for resolved requests
    resolved_requests = (
        db.query(AccessRequest)
        .filter(AccessRequest.provisioning_outcome != None)
        .all()
    )
    if resolved_requests:
        turnaround_hours = []
        for req in resolved_requests:
            delta = (req.updated_at - req.created_at).total_seconds() / 3600
            turnaround_hours.append(delta)
        access_request_turnaround = sum(turnaround_hours) / len(turnaround_hours)
    else:
        access_request_turnaround = 0.0

    # 9. Faithfulness pass rate — interactions where faithfulness_outcome=True / total checked
    faithfulness_checked = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.faithfulness_outcome != None)
        .scalar()
        or 0
    )
    faithfulness_passed = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.faithfulness_outcome == True)
        .scalar()
        or 0
    )
    faithfulness_pass_rate = (
        faithfulness_passed / faithfulness_checked
        if faithfulness_checked > 0
        else 1.0
    )

    # 10. Adversarial block rate — adversarial flagged / total interactions
    adversarial_flagged = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.adversarial_flag == True)
        .scalar()
        or 0
    )
    adversarial_block_rate = (
        (adversarial_flagged + guardrail_blocks) / total_queries
        if total_queries > 0
        else 0.0
    )

    # 11. User satisfaction score — average of non-null ratings
    avg_rating = (
        db.query(func.avg(Interaction.satisfaction_rating))
        .filter(Interaction.satisfaction_rating != None)
        .scalar()
    )
    user_satisfaction_score = float(avg_rating) if avg_rating is not None else 0.0

    total_escalations = db.query(func.count(Escalation.id)).scalar() or 0

    return AnalyticsMetrics(
        query_resolution_rate=round(query_resolution_rate, 4),
        escalation_rate=round(escalation_rate, 4),
        kb_coverage_rate=round(kb_coverage_rate, 4),
        model_correction_rate=round(model_correction_rate, 4),
        author_correction_rate=round(author_correction_rate, 4),
        action_success_rate=round(action_success_rate, 4),
        eligibility_block_rate=round(eligibility_block_rate, 4),
        access_request_turnaround=round(access_request_turnaround, 2),
        faithfulness_pass_rate=round(faithfulness_pass_rate, 4),
        adversarial_block_rate=round(adversarial_block_rate, 4),
        user_satisfaction_score=round(user_satisfaction_score, 2),
        total_queries=total_queries,
        total_escalations=total_escalations,
    )


# ---------------------------------------------------------------------------
# GET /analytics/reports/{report_id}
# ---------------------------------------------------------------------------

@router.get("/reports/{report_id}")
def get_report(report_id: str, db: DBSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Generate report R01–R10 as JSON data.
    """
    generators = {
        "R01": _report_query_volume,
        "R02": _report_escalation_breakdown,
        "R03": _report_kb_coverage,
        "R04": _report_faithfulness,
        "R05": _report_satisfaction,
        "R06": _report_guardrail_blocks,
        "R07": _report_access_requests,
        "R08": _report_article_lifecycle,
        "R09": _report_session_outcomes,
        "R10": _report_gap_log,
    }

    if report_id not in generators:
        raise HTTPException(
            status_code=404,
            detail=f"Report '{report_id}' not found. Available: R01–R10",
        )

    return generators[report_id](db)


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------

def _report_query_volume(db: DBSession) -> dict:
    total = db.query(func.count(Interaction.id)).scalar() or 0
    by_band = {}
    for band in ("HIGH", "LOW", "NONE"):
        count = (
            db.query(func.count(Interaction.id))
            .filter(Interaction.confidence_band == band)
            .scalar()
            or 0
        )
        by_band[band] = count
    return {
        "report": "R01",
        "title": "Query Volume by Confidence Band",
        "total_interactions": total,
        "by_confidence_band": by_band,
    }


def _report_escalation_breakdown(db: DBSession) -> dict:
    total = db.query(func.count(Escalation.id)).scalar() or 0
    by_status = {}
    for s in ("open", "in_progress", "resolved"):
        count = (
            db.query(func.count(Escalation.id))
            .filter(Escalation.resolution_status == s)
            .scalar()
            or 0
        )
        by_status[s] = count

    reason_counts: dict = {}
    for e in db.query(Escalation).all():
        reason = e.reason or "unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return {
        "report": "R02",
        "title": "Escalation Breakdown",
        "total_escalations": total,
        "by_status": by_status,
        "by_reason": reason_counts,
    }


def _report_kb_coverage(db: DBSession) -> dict:
    from models import Article, ArticleChunk

    total_articles = db.query(func.count(Article.id)).scalar() or 0
    published = (
        db.query(func.count(Article.id))
        .filter(Article.lifecycle_status == "published")
        .scalar()
        or 0
    )
    total_chunks = db.query(func.count(ArticleChunk.id)).scalar() or 0
    approved_chunks = (
        db.query(func.count(ArticleChunk.id))
        .filter(ArticleChunk.approved_status == True)
        .scalar()
        or 0
    )
    return {
        "report": "R03",
        "title": "Knowledge Base Coverage",
        "total_articles": total_articles,
        "published_articles": published,
        "total_article_chunks": total_chunks,
        "approved_chunks": approved_chunks,
    }


def _report_faithfulness(db: DBSession) -> dict:
    total_ff = db.query(func.count(FaithfulnessFailure.id)).scalar() or 0
    checked = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.faithfulness_outcome != None)
        .scalar()
        or 0
    )
    passed = (
        db.query(func.count(Interaction.id))
        .filter(Interaction.faithfulness_outcome == True)
        .scalar()
        or 0
    )
    return {
        "report": "R04",
        "title": "Faithfulness Check Results",
        "total_interactions_checked": checked,
        "faithfulness_passed": passed,
        "faithfulness_failed": total_ff,
        "pass_rate": round(passed / checked, 4) if checked > 0 else None,
    }


def _report_satisfaction(db: DBSession) -> dict:
    ratings = (
        db.query(Interaction.satisfaction_rating)
        .filter(Interaction.satisfaction_rating != None)
        .all()
    )
    values = [r[0] for r in ratings]
    avg = sum(values) / len(values) if values else None
    distribution: dict = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for v in values:
        distribution[v] = distribution.get(v, 0) + 1
    return {
        "report": "R05",
        "title": "User Satisfaction",
        "total_ratings": len(values),
        "average_rating": round(avg, 2) if avg else None,
        "distribution": distribution,
    }


def _report_guardrail_blocks(db: DBSession) -> dict:
    total = db.query(func.count(GuardrailBlock.id)).scalar() or 0
    pattern_counts: dict = {}
    for g in db.query(GuardrailBlock).all():
        p = g.matched_pattern or "unknown"
        pattern_counts[p] = pattern_counts.get(p, 0) + 1
    return {
        "report": "R06",
        "title": "Guardrail Blocks",
        "total_blocks": total,
        "by_pattern": pattern_counts,
    }


def _report_access_requests(db: DBSession) -> dict:
    total = db.query(func.count(AccessRequest.id)).scalar() or 0
    outcome_counts: dict = {}
    for r in db.query(AccessRequest).all():
        o = r.provisioning_outcome or "pending"
        outcome_counts[o] = outcome_counts.get(o, 0) + 1
    return {
        "report": "R07",
        "title": "Access Request Summary",
        "total_requests": total,
        "by_outcome": outcome_counts,
    }


def _report_article_lifecycle(db: DBSession) -> dict:
    from models import Article

    status_counts: dict = {}
    for s in ("draft", "pending_review", "published", "retired"):
        count = (
            db.query(func.count(Article.id))
            .filter(Article.lifecycle_status == s)
            .scalar()
            or 0
        )
        status_counts[s] = count
    return {
        "report": "R08",
        "title": "Article Lifecycle Summary",
        "by_status": status_counts,
    }


def _report_session_outcomes(db: DBSession) -> dict:
    status_counts: dict = {}
    for s in ("idle", "active", "troubleshooting", "resolved", "escalated"):
        count = (
            db.query(func.count(SessionModel.id))
            .filter(SessionModel.status == s)
            .scalar()
            or 0
        )
        status_counts[s] = count
    return {
        "report": "R09",
        "title": "Session Outcome Distribution",
        "by_status": status_counts,
    }


def _report_gap_log(db: DBSession) -> dict:
    from models import CoverageGapCluster

    gaps = (
        db.query(CoverageGapCluster)
        .order_by(CoverageGapCluster.occurrence_count.desc())
        .limit(20)
        .all()
    )
    return {
        "report": "R10",
        "title": "Top Coverage Gaps",
        "gaps": [
            {
                "representative_query": g.representative_query,
                "occurrence_count": g.occurrence_count,
                "classification_tag": g.classification_tag,
                "suggestion_status": g.suggestion_status,
            }
            for g in gaps
        ],
    }
