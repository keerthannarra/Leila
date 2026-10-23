"""
audit.py — Audit log viewer router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AuditLog
from schemas import AuditLogOut

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _audit_to_schema(a: AuditLog) -> AuditLogOut:
    details = None
    if a.event_details:
        try:
            details = json.loads(a.event_details)
        except Exception:
            details = {"raw": a.event_details}
    return AuditLogOut(
        id=a.id,
        event_type=a.event_type,
        actor_id=a.actor_id,
        event_details=details,
        data_classification_tag=a.data_classification_tag or "Public",
        timestamp=a.timestamp,
    )


@router.get("")
def list_audit_logs(
    request: Request,
    event_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    data_classification_tag: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """
    List audit log entries with optional filters.
    Supports CSV export: send Accept: text/csv header.
    """
    query = db.query(AuditLog)

    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if data_classification_tag:
        query = query.filter(
            AuditLog.data_classification_tag == data_classification_tag
        )
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    total = query.count()
    entries = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    # CSV export
    accept = request.headers.get("accept", "")
    if "text/csv" in accept:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["id", "event_type", "actor_id", "event_details", "data_classification_tag", "timestamp"]
        )
        for e in entries:
            writer.writerow(
                [
                    e.id,
                    e.event_type,
                    e.actor_id or "",
                    e.event_details or "",
                    e.data_classification_tag or "Public",
                    e.timestamp.isoformat() if e.timestamp else "",
                ]
            )
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )

    # JSON response
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": [_audit_to_schema(e) for e in entries],
    }
