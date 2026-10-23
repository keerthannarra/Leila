import type {
  Article,
  ChatMessage,
  ChatResponse,
  StepResponseOut,
  Escalation,
  AnalyticsMetrics,
  AuditLog,
  User,
  AccessRequest,
  Resource,
  AutomatedAction,
  FaithfulnessFailure,
  GuardrailBlock,
  CoverageGapCluster,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  // Get auth token
  const token = localStorage.getItem('leila_auth_token');
  
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options?.headers 
    },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return undefined as unknown as T;
}

export const api = {
  health: async () => {
    const healthPath = API_BASE.endsWith('/api')
      ? `${API_BASE.slice(0, -4)}/health`
      : '/health';
    const res = await fetch(healthPath);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json() as Promise<{ status: string }>;
  },

  chat: {
    getSessions: (userId: string) => 
      request<{ id: string, title: string, status: string, created_at: string }[]>(`/chat/sessions/${userId}`),
    getSessionHistory: (sessionId: string) =>
      request<{ messages: ChatMessage[] }>(`/chat/sessions/${sessionId}/history`),
    getHistory: (userId: string) => 
      request<{ messages: ChatMessage[] }>(`/chat/history/${userId}`),
    send: (userId: string, query: string, sessionId?: string) =>
      request<ChatResponse>('/chat', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, query, session_id: sessionId }),
      }),
    stepResponse: (
      sessionId: string,
      interactionId: string,
      stepIndex: number,
      resolved: boolean
    ) =>
      request<StepResponseOut>('/chat/step-response', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, interaction_id: interactionId, step_index: stepIndex, resolved }),
      }),
    rate: (interactionId: string, rating: number) =>
      request<void>(`/chat/rate/${interactionId}`, {
        method: 'POST',
        body: JSON.stringify({ rating }),
      }),
  },

  articles: {
    list: (status?: string, search?: string) => {
      const params = new URLSearchParams();
      if (status) params.set('lifecycle_status', status);
      if (search) params.set('search', search);
      const qs = params.toString();
      return request<Article[]>(`/articles${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => request<Article>(`/articles/${id}`),
    create: (data: Partial<Article>) =>
      request<Article>('/articles', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Article>) =>
      request<Article>(`/articles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    submit: (id: string) =>
      request<Article>(`/articles/${id}/submit`, { method: 'POST' }),
    approve: (id: string, approverId: string) =>
      request<Article>(`/articles/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ reviewer_id: approverId }),
      }),
    reject: (id: string, approverId: string, reason: string) =>
      request<Article>(`/articles/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reviewer_id: approverId, reason }),
      }),
    retire: (id: string) =>
      request<Article>(`/articles/${id}/retire`, { method: 'POST' }),
    uploadDocument: (file: File, uploaderId: string) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('uploader_id', uploaderId);
      return request<Record<string, unknown>>('/articles/upload-document', {
        method: 'POST',
        headers: {},
        body: formData,
      });
    },
    coverageGaps: () => request<CoverageGapCluster[]>('/articles/coverage-gaps'),
  },

  escalations: {
    list: (status?: string) => {
      const params = status ? `?status=${status}` : '';
      return request<Escalation[]>(`/escalations${params}`);
    },
    get: (id: string) => request<Escalation>(`/escalations/${id}`),
    assign: (id: string, agentId: string) =>
      request<Escalation>(`/escalations/${id}/assign`, {
        method: 'PUT',
        body: JSON.stringify({ agent_id: agentId }),
      }),
    resolve: (id: string, resolution: string) =>
      request<Escalation>(`/escalations/${id}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ resolution_notes: resolution }),
      }),
  },

  analytics: {
    metrics: () => request<AnalyticsMetrics>('/analytics/metrics'),
    report: (reportId: string, params?: Record<string, string>) => {
      const qs = params ? `?${new URLSearchParams(params)}` : '';
      return request<Record<string, unknown>>(`/analytics/reports/${reportId}${qs}`);
    },
  },

  audit: {
    list: (filters?: Record<string, string>) => {
      const qs = filters ? `?${new URLSearchParams(filters)}` : '';
      return request<AuditLog[]>(`/audit${qs}`);
    },
  },

  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; token_type: string; expires_in: number }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (name: string, email: string, password: string, role?: string, employmentType?: string) =>
      request<User>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role, employment_type: employmentType }),
      }),
    getCurrentUser: () => {
      const token = localStorage.getItem('leila_auth_token');
      if (!token) return null;
      return request<User>('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    logout: () => {
      const token = localStorage.getItem('leila_auth_token');
      localStorage.removeItem('leila_auth_token');
      localStorage.removeItem('leila_current_user');
      return request<any>('/auth/logout', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    },
  },

  users: {
    list: () => request<User[]>('/users'),
    create: (data: Partial<User>) =>
      request<User>('/users', { method: 'POST', body: JSON.stringify(data) }),
  },

  accessRequests: {
    list: (status?: string) => {
      const params = status ? `?status=${status}` : '';
      return request<AccessRequest[]>(`/access_requests${params}`);
    },
    create: (data: Partial<AccessRequest>) =>
      request<AccessRequest>('/access_requests', { method: 'POST', body: JSON.stringify(data) }),
    approve: (id: string, approverId: string) =>
      request<AccessRequest>(`/access_requests/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approver_id: approverId }),
      }),
    reject: (id: string, approverId: string, reason: string) =>
      request<AccessRequest>(`/access_requests/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ approver_id: approverId, reason }),
      }),
  },

  resources: {
    list: () => request<Resource[]>('/resources'),
    create: (data: Partial<Resource>) =>
      request<Resource>('/resources', { method: 'POST', body: JSON.stringify(data) }),
  },

  actions: {
    list: (status?: string) => {
      const params = status ? `?status=${status}` : '';
      return request<AutomatedAction[]>(`/actions${params}`);
    },
    create: (data: Partial<AutomatedAction>) =>
      request<AutomatedAction>('/actions', { method: 'POST', body: JSON.stringify(data) }),
    approve: (id: string, approverId: string) =>
      request<AutomatedAction>(`/actions/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ reviewer_id: approverId }),
      }),
  },

  faithfulnessFailures: {
    list: () => request<FaithfulnessFailure[]>('/faithfulness-failures'),
  },

  guardrailBlocks: {
    list: () => request<GuardrailBlock[]>('/guardrail-blocks'),
  },

  config: {
    get: () => request<Record<string, string>>('/configuration'),
    update: (key: string, value: string, changedBy: string) =>
      request<void>('/configuration', {
        method: 'PUT',
        body: JSON.stringify({ updates: { [key]: value }, changed_by: changedBy }),
      }),
  },
};
