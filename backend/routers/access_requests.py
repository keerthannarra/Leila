"""
access_requests.py — Access request and resource management router.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AccessRequest, AuditLog, Resource, User
from schemas import (
    AccessRequestApproveRequest,
    AccessRequestCreate,
    AccessRequestOut,
    AccessRequestRejectRequest,
    ResourceCreate,
    ResourceOut,
    ResourceUpdate,
)

router = APIRouter()

SLA_HOURS = 4  # BR-005: approver must respond within 4 business hours


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def log_audit(
    db: DBSession,
    event_type: str,
    actor_id: Optional[str],
    event_details: dict,
    data_classification_tag: str = "Internal",
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


def _access_request_to_schema(r: AccessRequest) -> AccessRequestOut:
    def _load(val):
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    return AccessRequestOut(
        id=r.id,
        requester_id=r.requester_id,
        resource_id=r.resource_id,
        reason=r.reason,
        cascade_instance=_load(r.cascade_instance),
        approval_history=_load(r.approval_history),
        sla_deadline=r.sla_deadline,
        provisioning_outcome=r.provisioning_outcome,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _resource_to_schema(r: Resource) -> ResourceOut:
    def _load(val):
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    return ResourceOut(
        id=r.id,
        name=r.name,
        category=r.category,
        owner_ids=_load(r.owner_ids),
        eligibility_rule=_load(r.eligibility_rule),
        approval_cascade=_load(r.approval_cascade),
        auto_delegation_rule=_load(r.auto_delegation_rule),
        created_at=r.created_at,
    )


# ---------------------------------------------------------------------------
# POST /access_requests
# ---------------------------------------------------------------------------

@router.post("/access_requests", response_model=AccessRequestOut, status_code=201)
def create_access_request(
    payload: AccessRequestCreate, db: DBSession = Depends(get_db)
):
    # Validate user and resource exist
    user = db.query(User).filter(User.id == payload.requester_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Requester user not found")

    resource = db.query(Resource).filter(Resource.id == payload.resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Build cascade instance from resource's approval_cascade
    cascade = []
    if resource.approval_cascade:
        try:
            cascade = json.loads(resource.approval_cascade)
        except Exception:
            cascade = []

    cascade_instance = {
        "cascade": cascade,
        "current_level": 0,
        "total_levels": len(cascade),
        "status": "pending" if cascade else "auto_approved",
    }

    now = _utcnow()
    sla_deadline = now + timedelta(hours=SLA_HOURS)

    request = AccessRequest(
        id=_new_uuid(),
        requester_id=payload.requester_id,
        resource_id=payload.resource_id,
        reason=payload.reason,
        cascade_instance=json.dumps(cascade_instance),
        approval_history=json.dumps([]),
        sla_deadline=sla_deadline,
        provisioning_outcome="granted" if not cascade else None,
        created_at=now,
        updated_at=now,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    log_audit(
        db,
        "access_request_created",
        payload.requester_id,
        {
            "request_id": request.id,
            "resource_id": payload.resource_id,
            "cascade_levels": len(cascade),
        },
    )

    return _access_request_to_schema(request)


# ---------------------------------------------------------------------------
# GET /access_requests
# ---------------------------------------------------------------------------

@router.get("/access_requests", response_model=List[AccessRequestOut])
def list_access_requests(
    status: Optional[str] = Query(None),
    db: DBSession = Depends(get_db),
):
    query = db.query(AccessRequest)
    if status == "pending":
        query = query.filter(AccessRequest.provisioning_outcome == None)
    elif status == "granted":
        query = query.filter(AccessRequest.provisioning_outcome == "granted")
    elif status == "rejected":
        query = query.filter(AccessRequest.provisioning_outcome == "rejected")
    requests = query.order_by(AccessRequest.created_at.desc()).all()
    return [_access_request_to_schema(r) for r in requests]


# ---------------------------------------------------------------------------
# POST /access_requests/{id}/approve
# ---------------------------------------------------------------------------

@router.post("/access_requests/{request_id}/approve", response_model=AccessRequestOut)
def approve_access_request(
    request_id: str,
    payload: AccessRequestApproveRequest,
    db: DBSession = Depends(get_db),
):
    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")

    if request.provisioning_outcome is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Request already has outcome: {request.provisioning_outcome}",
        )

    cascade_instance = json.loads(request.cascade_instance or "{}")
    approval_history = json.loads(request.approval_history or "[]")

    current_level = cascade_instance.get("current_level", 0)
    total_levels = cascade_instance.get("total_levels", 0)

    # Record approval
    approval_history.append(
        {
            "approver_id": payload.approver_id,
            "level": current_level,
            "action": "approved",
            "notes": payload.notes,
            "timestamp": _utcnow().isoformat(),
        }
    )

    next_level = current_level + 1
    if next_level >= total_levels:
        # Final approval — grant access
        request.provisioning_outcome = "granted"
        cascade_instance["status"] = "fully_approved"
    else:
        # Move to next approver level
        cascade_instance["current_level"] = next_level
        cascade_instance["status"] = "pending"

    request.cascade_instance = json.dumps(cascade_instance)
    request.approval_history = json.dumps(approval_history)
    request.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "access_request_approved",
        payload.approver_id,
        {
            "request_id": request_id,
            "level": current_level,
            "final": next_level >= total_levels,
        },
    )

    return _access_request_to_schema(request)


# ---------------------------------------------------------------------------
# POST /access_requests/{id}/reject
# ---------------------------------------------------------------------------

@router.post("/access_requests/{request_id}/reject", response_model=AccessRequestOut)
def reject_access_request(
    request_id: str,
    payload: AccessRequestRejectRequest,
    db: DBSession = Depends(get_db),
):
    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")

    if request.provisioning_outcome is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Request already has outcome: {request.provisioning_outcome}",
        )

    approval_history = json.loads(request.approval_history or "[]")
    approval_history.append(
        {
            "approver_id": payload.approver_id,
            "action": "rejected",
            "reason": payload.reason,
            "timestamp": _utcnow().isoformat(),
        }
    )

    cascade_instance = json.loads(request.cascade_instance or "{}")
    cascade_instance["status"] = "rejected"

    request.provisioning_outcome = "rejected"
    request.cascade_instance = json.dumps(cascade_instance)
    request.approval_history = json.dumps(approval_history)
    request.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "access_request_rejected",
        payload.approver_id,
        {"request_id": request_id, "reason": payload.reason},
    )

    return _access_request_to_schema(request)


# ---------------------------------------------------------------------------
# GET /resources
# ---------------------------------------------------------------------------

@router.get("/resources", response_model=List[ResourceOut])
def list_resources(db: DBSession = Depends(get_db)):
    resources = db.query(Resource).order_by(Resource.created_at).all()
    return [_resource_to_schema(r) for r in resources]


# ---------------------------------------------------------------------------
# POST /resources
# ---------------------------------------------------------------------------

@router.post("/resources", response_model=ResourceOut, status_code=201)
def create_resource(payload: ResourceCreate, db: DBSession = Depends(get_db)):
    # Validate cascade depth ≤ 3
    cascade = payload.approval_cascade or []
    if len(cascade) > 3:
        raise HTTPException(
            status_code=400,
            detail="Approval cascade depth cannot exceed 3 levels.",
        )

    resource = Resource(
        id=_new_uuid(),
        name=payload.name,
        category=payload.category,
        owner_ids=json.dumps(payload.owner_ids) if payload.owner_ids else None,
        eligibility_rule=(
            json.dumps(payload.eligibility_rule) if payload.eligibility_rule else None
        ),
        approval_cascade=json.dumps(cascade),
        auto_delegation_rule=(
            json.dumps(payload.auto_delegation_rule)
            if payload.auto_delegation_rule
            else None
        ),
        created_at=_utcnow(),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    log_audit(
        db,
        "resource_created",
        None,
        {"resource_id": resource.id, "name": resource.name},
    )

    return _resource_to_schema(resource)


# ---------------------------------------------------------------------------
# PUT /resources/{id}
# ---------------------------------------------------------------------------

@router.put("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: str, payload: ResourceUpdate, db: DBSession = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if payload.name is not None:
        resource.name = payload.name
    if payload.category is not None:
        resource.category = payload.category
    if payload.owner_ids is not None:
        resource.owner_ids = json.dumps(payload.owner_ids)
    if payload.eligibility_rule is not None:
        resource.eligibility_rule = json.dumps(payload.eligibility_rule)
    if payload.approval_cascade is not None:
        if len(payload.approval_cascade) > 3:
            raise HTTPException(
                status_code=400,
                detail="Approval cascade depth cannot exceed 3 levels.",
            )
        resource.approval_cascade = json.dumps(payload.approval_cascade)
    if payload.auto_delegation_rule is not None:
        resource.auto_delegation_rule = json.dumps(payload.auto_delegation_rule)

    db.commit()
    db.refresh(resource)

    log_audit(
        db,
        "resource_updated",
        None,
        {"resource_id": resource_id},
    )

    return _resource_to_schema(resource)
