import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Float,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(
        SAEnum(
            "employee",
            "it_support_agent",
            "it_content_owner",
            "it_operations_lead",
            "it_operations_manager",
            "resource_owner",
            "administrator",
            "compliance_reviewer",
            name="user_role_enum",
        ),
        nullable=False,
        default="employee",
    )
    employment_type = Column(String, nullable=True)
    manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    manager = relationship("User", remote_side="User.id", foreign_keys=[manager_id])
    articles_authored = relationship("Article", back_populates="author", foreign_keys="Article.author_id")
    articles_reviewed = relationship("Article", back_populates="reviewer", foreign_keys="Article.reviewer_id")
    sessions = relationship("Session", back_populates="user")
    escalations_assigned = relationship("Escalation", back_populates="assigned_agent", foreign_keys="Escalation.assigned_agent_id")


class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, default=new_uuid)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    steps = Column(Text, nullable=True)  # JSON list of step strings
    category = Column(String, nullable=True)
    context_tags = Column(Text, nullable=True)  # JSON list of strings
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    author_type = Column(
        SAEnum("human", "agent_drafted", name="author_type_enum"),
        nullable=False,
        default="human",
    )
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    lifecycle_status = Column(
        SAEnum("draft", "pending_review", "published", "retired", name="article_status_enum"),
        nullable=False,
        default="draft",
    )
    review_cycle_days = Column(Integer, default=90)
    last_reviewed_date = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    author = relationship("User", back_populates="articles_authored", foreign_keys=[author_id])
    reviewer = relationship("User", back_populates="articles_reviewed", foreign_keys=[reviewer_id])
    chunks = relationship("ArticleChunk", back_populates="article", cascade="all, delete-orphan")


class ArticleChunk(Base):
    __tablename__ = "article_chunks"

    id = Column(String, primary_key=True, default=new_uuid)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON list of floats
    chunk_order = Column(Integer, nullable=False)
    approved_status = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    article = relationship("Article", back_populates="chunks")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=new_uuid)
    filename = Column(String, nullable=False)
    source_type = Column(
        SAEnum("pdf", "docx", "md", "txt", name="doc_source_type_enum"),
        nullable=False,
    )
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    uploader = relationship("User")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=new_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON list of floats
    chunk_order = Column(Integer, nullable=False)
    approved_status = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")


class AutomatedAction(Base):
    __tablename__ = "automated_actions"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    parameter_schema = Column(Text, nullable=True)  # JSON
    eligibility_rule = Column(Text, nullable=True)  # JSON
    approval_required = Column(Boolean, default=False)
    lifecycle_status = Column(
        SAEnum("draft", "pending_review", "published", "retired", name="action_status_enum"),
        nullable=False,
        default="draft",
    )
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    author = relationship("User", foreign_keys=[author_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    owner_ids = Column(Text, nullable=True)  # JSON list of user IDs
    eligibility_rule = Column(Text, nullable=True)  # JSON
    approval_cascade = Column(Text, nullable=True)  # JSON list of approver configs (max depth 3)
    auto_delegation_rule = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    access_requests = relationship("AccessRequest", back_populates="resource")


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(String, primary_key=True, default=new_uuid)
    requester_id = Column(String, ForeignKey("users.id"), nullable=False)
    resource_id = Column(String, ForeignKey("resources.id"), nullable=False)
    reason = Column(Text, nullable=True)
    cascade_instance = Column(Text, nullable=True)  # JSON — current approver state
    approval_history = Column(Text, nullable=True)  # JSON list of approval records
    sla_deadline = Column(DateTime, nullable=True)
    provisioning_outcome = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id])
    resource = relationship("Resource", back_populates="access_requests")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(
        SAEnum("idle", "active", "troubleshooting", "resolved", "escalated", name="session_status_enum"),
        nullable=False,
        default="idle",
    )
    created_at = Column(DateTime, default=utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    interactions = relationship("Interaction", back_populates="session")
    escalations = relationship("Escalation", back_populates="session")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=new_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel = Column(String, default="web_chat")
    query_text = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    matched_article_ids = Column(Text, nullable=True)  # JSON list
    confidence_band = Column(
        SAEnum("HIGH", "LOW", "NONE", name="confidence_band_enum"),
        nullable=True,
    )
    response_text = Column(Text, nullable=True)
    steps_presented = Column(Text, nullable=True)  # JSON list
    action_invocations = Column(Text, nullable=True)  # JSON list
    escalation_flag = Column(Boolean, default=False)
    jira_reference = Column(String, nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)
    faithfulness_outcome = Column(Boolean, nullable=True)
    adversarial_flag = Column(Boolean, default=False)
    data_classification_tag = Column(
        SAEnum("Public", "Internal", "Confidential", "Restricted", name="data_class_enum"),
        default="Public",
    )
    timestamp = Column(DateTime, default=utcnow)

    # Relationships
    session = relationship("Session", back_populates="interactions")
    user = relationship("User")
    steps = relationship("InteractionStep", back_populates="interaction", cascade="all, delete-orphan")
    faithfulness_failures = relationship("FaithfulnessFailure", back_populates="interaction")


class InteractionStep(Base):
    __tablename__ = "interaction_steps"

    id = Column(String, primary_key=True, default=new_uuid)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_content = Column(Text, nullable=False)
    user_response = Column(String, nullable=True)
    step_timestamp = Column(DateTime, default=utcnow)

    # Relationships
    interaction = relationship("Interaction", back_populates="steps")


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, default=new_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    original_query = Column(Text, nullable=False)
    matched_articles = Column(Text, nullable=True)  # JSON list
    steps_attempted = Column(Text, nullable=True)  # JSON list
    actions_attempted = Column(Text, nullable=True)  # JSON list
    reason = Column(Text, nullable=True)
    jira_reference = Column(String, nullable=True)
    assigned_agent_id = Column(String, ForeignKey("users.id"), nullable=True)
    resolution_status = Column(
        SAEnum("open", "in_progress", "resolved", name="resolution_status_enum"),
        nullable=False,
        default="open",
    )
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    session = relationship("Session", back_populates="escalations")
    assigned_agent = relationship("User", back_populates="escalations_assigned", foreign_keys=[assigned_agent_id])


class CoverageGapCluster(Base):
    __tablename__ = "coverage_gap_clusters"

    id = Column(String, primary_key=True, default=new_uuid)
    representative_query = Column(Text, nullable=False)
    occurrence_count = Column(Integer, default=1)
    member_query_ids = Column(Text, nullable=True)  # JSON list of interaction IDs
    classification_tag = Column(
        SAEnum("information_gap", "action_shaped", name="gap_class_enum"),
        nullable=True,
    )
    auto_tag_source = Column(String, nullable=True)
    suggestion_status = Column(
        SAEnum("open", "actioned", "dismissed", name="suggestion_status_enum"),
        nullable=False,
        default="open",
    )
    closing_artefact_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=new_uuid)
    event_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=True)
    event_details = Column(Text, nullable=True)  # JSON
    data_classification_tag = Column(String, default="Public")
    timestamp = Column(DateTime, default=utcnow)
    # Append-only — no update or delete operations permitted


class GuardrailBlock(Base):
    __tablename__ = "guardrail_blocks"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, nullable=True)
    blocked_query = Column(Text, nullable=False)
    matched_pattern = Column(String, nullable=True)
    block_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utcnow)


class FaithfulnessFailure(Base):
    __tablename__ = "faithfulness_failures"

    id = Column(String, primary_key=True, default=new_uuid)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=True)
    original_query = Column(Text, nullable=False)
    llm_answer = Column(Text, nullable=False)
    unsupported_claims = Column(Text, nullable=True)  # JSON list
    retrieved_chunks = Column(Text, nullable=True)  # JSON list
    timestamp = Column(DateTime, default=utcnow)

    # Relationships
    interaction = relationship("Interaction", back_populates="faithfulness_failures")


class ConfigurationEvent(Base):
    __tablename__ = "configuration_events"

    id = Column(String, primary_key=True, default=new_uuid)
    parameter_name = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    changed_by = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow)


class RateLimitTracking(Base):
    __tablename__ = "rate_limit_tracking"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, unique=True, nullable=False)
    query_count = Column(Integer, default=0)
    window_start_time = Column(DateTime, nullable=False)
    last_query_time = Column(DateTime, nullable=False)
