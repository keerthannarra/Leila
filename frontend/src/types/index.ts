export type Role =
  | 'employee'
  | 'it_support_agent'
  | 'it_content_owner'
  | 'it_operations_lead'
  | 'it_operations_manager'
  | 'resource_owner'
  | 'administrator'
  | 'compliance_reviewer';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  employment_type?: string;
  manager_id?: string;
}

export interface Step {
  content: string;
  order: number;
}

export interface Article {
  id: string;
  title: string;
  content: string;
  steps: string[];
  category: string;
  context_tags: string[];
  author_id: string;
  author_type: 'human' | 'agent_drafted';
  reviewer_id?: string;
  lifecycle_status: 'draft' | 'pending_review' | 'published' | 'retired';
  review_cycle_days: number;
  last_reviewed_date?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  type?: 'answer' | 'step' | 'escalation' | 'rating_prompt';
  metadata?: Record<string, unknown>;
}

export interface ChatResponse {
  response: string;
  confidence_band: 'HIGH' | 'LOW' | 'NONE';
  session_id: string;
  interaction_id: string;
  escalated: boolean;
  jira_reference?: string;
  steps?: string[];       // present for troubleshooting articles (HIGH confidence)
  ask_relevance: boolean; // true when confidence is LOW — ask user if match is relevant
}

export interface StepResponseOut {
  message: string;
  next_step?: string;
  step_index?: number;
  session_status: string;
  escalated: boolean;
  jira_reference?: string;
  prompt_rating: boolean;
}

export interface Escalation {
  id: string;
  session_id: string;
  original_query: string;
  matched_articles?: string[];
  steps_attempted?: string[];
  actions_attempted?: string[];
  reason?: string;
  jira_reference?: string;
  jira_url?: string;
  assigned_agent_id?: string;
  resolution_status: 'open' | 'in_progress' | 'resolved';
  created_at: string;
  updated_at: string;
}

export interface AnalyticsMetrics {
  query_resolution_rate: number;
  escalation_rate: number;
  kb_coverage_rate: number;
  model_correction_rate: number;
  author_correction_rate: number;
  action_success_rate: number;
  eligibility_block_rate: number;
  access_request_turnaround: number;
  faithfulness_pass_rate: number;
  adversarial_block_rate: number;
  user_satisfaction_score: number;
  total_queries: number;
  total_escalations: number;
}

export interface AuditLog {
  id: string;
  event_type: string;
  actor_id?: string;
  event_details: Record<string, unknown>;
  data_classification_tag: string;
  timestamp: string;
}

export interface ApprovalRecord {
  approver_id: string;
  decision: string;
  timestamp: string;
  comment?: string;
}

export interface AccessRequest {
  id: string;
  requester_id: string;
  resource_id: string;
  reason: string;
  approval_history: ApprovalRecord[];
  sla_deadline: string;
  provisioning_outcome?: string;
  created_at: string;
}

export interface AutomatedAction {
  id: string;
  name: string;
  description: string;
  parameter_schema: Record<string, unknown>;
  eligibility_rule: Record<string, unknown>;
  approval_required: boolean;
  lifecycle_status: string;
  author_id: string;
  reviewer_id?: string;
  created_at: string;
}

export interface Resource {
  id: string;
  name: string;
  category: string;
  owner_ids: string[];
  eligibility_rule: Record<string, unknown>;
  approval_cascade: Record<string, unknown>[];
  created_at: string;
}

export interface FaithfulnessFailure {
  id: string;
  interaction_id: string;
  original_query: string;
  llm_answer: string;
  unsupported_claims: Record<string, unknown>[];
  retrieved_chunks: Record<string, unknown>[];
  timestamp: string;
}

export interface GuardrailBlock {
  id: string;
  user_id?: string;
  blocked_query: string;
  matched_pattern: string;
  block_reason: string;
  timestamp: string;
}

export interface CoverageGapCluster {
  id: string;
  representative_query: string;
  occurrence_count: number;
  classification_tag: string;
  suggestion_status: string;
  created_at: string;
}

export interface ConfigParam {
  key: string;
  value: string;
  description: string;
  changed_by?: string;
  changed_at?: string;
}
