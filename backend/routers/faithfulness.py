"""
faithfulness.py — Faithfulness failure review router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AuditLog, FaithfulnessFailure
from schemas import FaithfulnessClassifyRequest, FaithfulnessFailureOut

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
) -> None:
    entry = AuditLog(
        id=_new_uuid(),
        event_type=event_type,
        actor_id=actor_id,
        event_details=json.dumps(event_details),
        data_classification_tag="Internal",
        timestamp=_utcnow(),
    )
    db.add(entry)
    db.commit()


def _ff_to_schema(f: FaithfulnessFailure) -> FaithfulnessFailureOut:
    def _load(val):
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    return FaithfulnessFailureOut(
        id=f.id,
        interaction_id=f.interaction_id,
        original_query=f.original_query,
        llm_answer=f.llm_answer,
        unsupported_claims=_load(f.unsupported_claims),
        retrieved_chunks=_load(f.retrieved_chunks),
        timestamp=f.timestamp,
    )


# ---------------------------------------------------------------------------
# GET /faithfulness-failures
# ---------------------------------------------------------------------------

@router.get("", response_model=List[FaithfulnessFailureOut])
def list_faithfulness_failures(
    interaction_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    query = db.query(FaithfulnessFailure)
    if interaction_id:
        query = query.filter(FaithfulnessFailure.interaction_id == interaction_id)
    total = query.count()
    failures = (
        query.order_by(FaithfulnessFailure.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_ff_to_schema(f) for f in failures]


# ---------------------------------------------------------------------------
# POST /faithfulness-failures/{id}/classify
# ---------------------------------------------------------------------------

@router.post("/{failure_id}/classify")
def classify_faithfulness_failure(
    failure_id: str,
    payload: FaithfulnessClassifyRequest,
    db: DBSession = Depends(get_db),
):
    """IT Ops Lead classifies the root cause of a faithfulness failure."""
    failure = (
        db.query(FaithfulnessFailure)
        .filter(FaithfulnessFailure.id == failure_id)
        .first()
    )
    if not failure:
        raise HTTPException(status_code=404, detail="Faithfulness failure not found")

    # Store classification in unsupported_claims as metadata
    existing = json.loads(failure.unsupported_claims or "[]")
    classification_entry = {
        "classified_by": payload.classified_by,
        "root_cause": payload.root_cause,
        "classified_at": _utcnow().isoformat(),
    }
    if isinstance(existing, list):
        existing.append({"_classification": classification_entry})
    failure.unsupported_claims = json.dumps(existing)
    db.commit()

    log_audit(
        db,
        "faithfulness_failure_classified",
        payload.classified_by,
        {
            "failure_id": failure_id,
            "root_cause": payload.root_cause,
        },
    )

    return {
        "message": "Root cause classification recorded.",
        "failure_id": failure_id,
        "root_cause": payload.root_cause,
        "classified_by": payload.classified_by,
    }
