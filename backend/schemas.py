from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: str
    query: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    confidence_band: str  # HIGH / LOW / NONE
    session_id: str
    interaction_id: str
    escalated: bool = False
    jira_reference: Optional[str] = None
    steps: Optional[List[str]] = None
    ask_relevance: bool = False  # True when confidence band is LOW


class StepResponseRequest(BaseModel):
    session_id: str
    interaction_id: str
    step_index: int
    resolved: bool


class StepResponseOut(BaseModel):
    message: str
    next_step: Optional[str] = None
    step_index: Optional[int] = None
    session_status: str
    escalated: bool = False
    jira_reference: Optional[str] = None
    prompt_rating: bool = False


class SatisfactionRating(BaseModel):
    rating: int = Field(..., ge=1, le=5)


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    name: str
    email: str
    role: str = "employee"
    employment_type: Optional[str] = None
    manager_id: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    employment_type: Optional[str] = None
    manager_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Article schemas
# ---------------------------------------------------------------------------

class ArticleCreate(BaseModel):
    title: str
    content: str
    steps: Optional[List[str]] = None
    category: Optional[str] = None
    context_tags: Optional[List[str]] = None
    author_id: str
    author_type: str = "human"


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    steps: Optional[List[str]] = None
    category: Optional[str] = None
    context_tags: Optional[List[str]] = None


class ArticleOut(BaseModel):
    id: str
    title: str
    content: str
    steps: Optional[List[str]] = None
    category: Optional[str] = None
    context_tags: Optional[List[str]] = None
    author_id: str
    author_type: str
    reviewer_id: Optional[str] = None
    lifecycle_status: str
    review_cycle_days: int
    last_reviewed_date: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleApproveRequest(BaseModel):
    reviewer_id: str


class ArticleRejectRequest(BaseModel):
    reviewer_id: str
    reason: str


# ---------------------------------------------------------------------------
# Escalation schemas
# ---------------------------------------------------------------------------

class EscalationOut(BaseModel):
    id: str
    session_id: str
    original_query: str
    matched_articles: Optional[List[str]] = None
    steps_attempted: Optional[List[str]] = None
    actions_attempted: Optional[List[str]] = None
    reason: Optional[str] = None
    jira_reference: Optional[str] = None
    jira_url: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    resolution_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EscalationAssignRequest(BaseModel):
    agent_id: str


class EscalationResolveRequest(BaseModel):
    resolution_notes: str
    create_article: bool = False
    article_title: Optional[str] = None
    article_author_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------

class AnalyticsMetrics(BaseModel):
    query_resolution_rate: float
    escalation_rate: float
    kb_coverage_rate: float
    model_correction_rate: float
    author_correction_rate: float
    action_success_rate: float
    eligibility_block_rate: float
    access_request_turnaround: float
    faithfulness_pass_rate: float
    adversarial_block_rate: float
    user_satisfaction_score: float
    total_queries: int = 0
    total_escalations: int = 0

    model_config = {
        "protected_namespaces": (),
    }


# ---------------------------------------------------------------------------
# Access Request schemas
# ---------------------------------------------------------------------------

class AccessRequestCreate(BaseModel):
    requester_id: str
    resource_id: str
    reason: Optional[str] = None


class AccessRequestOut(BaseModel):
    id: str
    requester_id: str
    resource_id: str
    reason: Optional[str] = None
    cascade_instance: Optional[Dict[str, Any]] = None
    approval_history: Optional[List[Dict[str, Any]]] = None
    sla_deadline: Optional[datetime] = None
    provisioning_outcome: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccessRequestApproveRequest(BaseModel):
    approver_id: str
    notes: Optional[str] = None


class AccessRequestRejectRequest(BaseModel):
    approver_id: str
    reason: str


# ---------------------------------------------------------------------------
# Resource schemas
# ---------------------------------------------------------------------------

class ResourceCreate(BaseModel):
    name: str
    category: Optional[str] = None
    owner_ids: Optional[List[str]] = None
    eligibility_rule: Optional[Dict[str, Any]] = None
    approval_cascade: Optional[List[Dict[str, Any]]] = None
    auto_delegation_rule: Optional[Dict[str, Any]] = None


class ResourceOut(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    owner_ids: Optional[List[str]] = None
    eligibility_rule: Optional[Dict[str, Any]] = None
    approval_cascade: Optional[List[Dict[str, Any]]] = None
    auto_delegation_rule: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    owner_ids: Optional[List[str]] = None
    eligibility_rule: Optional[Dict[str, Any]] = None
    approval_cascade: Optional[List[Dict[str, Any]]] = None
    auto_delegation_rule: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Audit Log schemas
# ---------------------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: str
    event_type: str
    actor_id: Optional[str] = None
    event_details: Optional[Dict[str, Any]] = None
    data_classification_tag: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AutomatedAction schemas
# ---------------------------------------------------------------------------

class ActionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    eligibility_rule: Optional[Dict[str, Any]] = None
    approval_required: bool = False
    author_id: str


class ActionOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    eligibility_rule: Optional[Dict[str, Any]] = None
    approval_required: bool
    lifecycle_status: str
    author_id: str
    reviewer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActionApproveRequest(BaseModel):
    reviewer_id: str


class ActionRejectRequest(BaseModel):
    reviewer_id: str
    reason: str


# ---------------------------------------------------------------------------
# Session schemas
# ---------------------------------------------------------------------------

class SessionOut(BaseModel):
    id: str
    user_id: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Faithfulness / Guardrail schemas
# ---------------------------------------------------------------------------

class FaithfulnessFailureOut(BaseModel):
    id: str
    interaction_id: str
    original_query: str
    llm_answer: str
    unsupported_claims: Optional[List[Dict[str, Any]]] = None
    retrieved_chunks: Optional[List[str]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class FaithfulnessClassifyRequest(BaseModel):
    root_cause: str
    classified_by: str


class GuardrailBlockOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    blocked_query: str
    matched_pattern: Optional[str] = None
    block_reason: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Configuration schemas
# ---------------------------------------------------------------------------

class ConfigurationUpdate(BaseModel):
    updates: Dict[str, str]
    changed_by: Optional[str] = None


class ConfigurationOut(BaseModel):
    parameters: Dict[str, str]
