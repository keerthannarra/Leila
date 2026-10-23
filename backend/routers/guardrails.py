"""
guardrails.py — Guardrail blocks and system configuration router.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AuditLog, ConfigurationEvent, GuardrailBlock
from schemas import ConfigurationOut, ConfigurationUpdate, GuardrailBlockOut

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


def _gb_to_schema(g: GuardrailBlock) -> GuardrailBlockOut:
    return GuardrailBlockOut(
        id=g.id,
        user_id=g.user_id,
        blocked_query=g.blocked_query,
        matched_pattern=g.matched_pattern,
        block_reason=g.block_reason,
        timestamp=g.timestamp,
    )


# ---------------------------------------------------------------------------
# GET /guardrail-blocks
# ---------------------------------------------------------------------------

@router.get("/guardrail-blocks", response_model=List[GuardrailBlockOut])
def list_guardrail_blocks(
    user_id: Optional[str] = Query(None),
    matched_pattern: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    query = db.query(GuardrailBlock)
    if user_id:
        query = query.filter(GuardrailBlock.user_id == user_id)
    if matched_pattern:
        query = query.filter(GuardrailBlock.matched_pattern == matched_pattern)
    blocks = (
        query.order_by(GuardrailBlock.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_gb_to_schema(g) for g in blocks]


# ---------------------------------------------------------------------------
# GET /configuration
# ---------------------------------------------------------------------------

@router.get("/configuration", response_model=ConfigurationOut)
def get_configuration(db: DBSession = Depends(get_db)):
    """Return the latest value for every known configuration parameter."""
    # Fetch all config events, pick the latest per parameter_name
    all_events = (
        db.query(ConfigurationEvent)
        .order_by(ConfigurationEvent.timestamp.desc())
        .all()
    )

    latest: Dict[str, str] = {}
    for event in all_events:
        if event.parameter_name not in latest:
            latest[event.parameter_name] = event.new_value

    # Merge with default values if not yet set
    defaults: Dict[str, str] = {
        "rate_limit_queries_per_window": "60",
        "rate_limit_window_minutes": "5",
        "rag_top_k": "5",
        "confidence_high_threshold": "0.50",
        "confidence_low_threshold": "0.35",
        "faithfulness_pass_threshold": "0.85",
        "sla_approver_response_hours": "4",
        "review_cycle_days": "90",
        "max_cascade_depth": "3",
        "max_troubleshooting_steps": "10",
    }
    for k, v in defaults.items():
        if k not in latest:
            latest[k] = v

    return ConfigurationOut(parameters=latest)


# ---------------------------------------------------------------------------
# PUT /configuration
# ---------------------------------------------------------------------------

@router.put("/configuration", response_model=ConfigurationOut)
def update_configuration(
    payload: ConfigurationUpdate, db: DBSession = Depends(get_db)
):
    """Update configuration values and log each change as a ConfigurationEvent."""
    if not payload.updates:
        raise HTTPException(status_code=400, detail="No updates provided.")

    # Get current values for old_value recording
    current_events = (
        db.query(ConfigurationEvent)
        .order_by(ConfigurationEvent.timestamp.desc())
        .all()
    )
    current_values: Dict[str, str] = {}
    for event in current_events:
        if event.parameter_name not in current_values:
            current_values[event.parameter_name] = event.new_value

    for param_name, new_value in payload.updates.items():
        old_value = current_values.get(param_name)
        config_event = ConfigurationEvent(
            id=_new_uuid(),
            parameter_name=param_name,
            old_value=old_value,
            new_value=new_value,
            changed_by=payload.changed_by,
            timestamp=_utcnow(),
        )
        db.add(config_event)

    db.commit()

    log_audit(
        db,
        "configuration_updated",
        payload.changed_by,
        {"parameters_changed": list(payload.updates.keys())},
    )

    # Return updated configuration
    return get_configuration(db)
