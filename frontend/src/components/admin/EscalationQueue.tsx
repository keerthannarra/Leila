import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Clock, ExternalLink, UserCheck } from 'lucide-react';
import { format, differenceInHours } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { Escalation } from '../../types';
import { StatusBadge } from '../shared/StatusBadge';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { EmptyState } from '../shared/EmptyState';
import { Spinner } from '../shared/Spinner';

type Filter = 'all' | 'open' | 'in_progress' | 'resolved';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'resolved', label: 'Resolved' },
];

function SlaTimer({ createdAt }: { createdAt: string }) {
  const hoursSince = differenceInHours(new Date(), new Date(createdAt));
  const slaHours = 4;
  const remaining = slaHours - hoursSince;
  const isBreached = remaining <= 0;
  const isWarning = remaining <= 2;

  return (
    <span className={`flex items-center gap-1 text-xs font-medium ${
      isBreached ? 'text-red-600' : isWarning ? 'text-yellow-600' : 'text-gray-500'
    }`}>
      <Clock size={11} />
      {isBreached ? `Breached by ${Math.abs(remaining)}h` : `${remaining}h remaining`}
    </span>
  );
}

export function EscalationQueue() {
  const { currentRole, currentUser } = useRole();
  const { showToast } = useToast();
  const [filter, setFilter] = useState<Filter>('all');
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [resolveTarget, setResolveTarget] = useState<Escalation | null>(null);
  const [resolution, setResolution] = useState('');
  const [createArticle, setCreateArticle] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const isReadOnly = currentRole === 'it_operations_manager';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.escalations.list(filter === 'all' ? undefined : filter);
      setEscalations(data);
    } catch {
      setEscalations([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const handleAssign = async (escalationId: string) => {
    if (!currentUser) return;
    setActionLoading(true);
    try {
      await api.escalations.assign(escalationId, currentUser.id);
      showToast('Escalation assigned to you successfully', 'success');
      load();
    } catch {
      showToast('Failed to assign escalation', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!resolveTarget || !resolution.trim()) return;
    setActionLoading(true);
    try {
      await api.escalations.resolve(resolveTarget.id, resolution);
      showToast('Escalation resolved successfully', 'success');
      setResolveTarget(null);
      setResolution('');
      setCreateArticle(false);
      load();
    } catch {
      showToast('Failed to resolve escalation', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <h1 className="text-lg font-bold text-gray-900">Escalation Queue</h1>
        <p className="text-sm text-gray-500">
          {isReadOnly ? 'View escalation statuses and resolutions' : 'Manage and resolve escalated IT queries'}
        </p>
        <div className="flex gap-1 mt-4">
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                filter === f.key ? 'bg-brand-700 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : escalations.length === 0 ? (
            <EmptyState
              title="No escalations found"
              description="No escalations match the current filter."
              icon={<AlertTriangle size={40} />}
            />
          ) : (
            <div className="divide-y divide-gray-100">
              {escalations.map(esc => {
                const isOpen = expanded === esc.id;
                return (
                  <div key={esc.id}>
                    <div
                      className="flex items-center gap-4 px-4 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => setExpanded(isOpen ? null : esc.id)}
                    >
                      <div className="flex-1 min-w-0 grid grid-cols-5 gap-4 items-center">
                        {/* JIRA ref */}
                        <div className="col-span-1">
                          {esc.jira_reference ? (
                            <a
                              href={esc.jira_url || `#`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-xs font-mono text-brand-600 hover:text-brand-700 transition-colors"
                            >
                              <ExternalLink size={11} />
                              {esc.jira_reference}
                            </a>
                          ) : <span className="text-xs text-gray-400">—</span>}
                        </div>
                        {/* Query */}
                        <div className="col-span-2">
                          <p className="text-sm text-gray-800 truncate">{esc.original_query}</p>
                          <p className="text-xs text-gray-400 mt-0.5">{esc.reason}</p>
                        </div>
                        {/* Status + SLA */}
                        <div className="col-span-1 space-y-1">
                          <StatusBadge status={esc.resolution_status} />
                          {esc.resolution_status !== 'resolved' && (
                            <SlaTimer createdAt={esc.created_at} />
                          )}
                        </div>
                        {/* Agent */}
                        <div className="col-span-1 text-xs text-gray-500 truncate">
                          {esc.assigned_agent_id ?? <span className="text-gray-300">Unassigned</span>}
                        </div>
                      </div>
                      {isOpen ? <ChevronUp size={16} className="text-gray-400 flex-shrink-0" /> : <ChevronDown size={16} className="text-gray-400 flex-shrink-0" />}
                    </div>

                    {/* Expanded detail */}
                    {isOpen && (
                      <div className="bg-blue-50 px-6 py-4 space-y-4 border-t border-blue-100">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Original Query</h4>
                            <p className="text-sm text-gray-800">{esc.original_query}</p>
                          </div>
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Escalation Reason</h4>
                            <p className="text-sm text-gray-800">{esc.reason}</p>
                          </div>
                        </div>
                        {esc.steps_attempted && esc.steps_attempted.length > 0 && (
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Steps Attempted</h4>
                            <ul className="space-y-1">
                              {esc.steps_attempted.map((step, i) => (
                                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                                  <span className="w-4 h-4 rounded-full bg-gray-200 text-gray-600 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                                  {step}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Clock size={12} />
                          Created {format(new Date(esc.created_at), 'MMM d, yyyy HH:mm')}
                        </div>

                        {!isReadOnly && esc.resolution_status !== 'resolved' && (
                          <div className="flex gap-2">
                            {!esc.assigned_agent_id && (
                              <button
                                onClick={() => handleAssign(esc.id)}
                                disabled={actionLoading}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
                              >
                                <UserCheck size={14} /> Assign to Me
                              </button>
                            )}
                            <button
                              onClick={() => setResolveTarget(esc)}
                              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
                            >
                              Resolve
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Resolve Modal */}
      <Modal open={!!resolveTarget} onClose={() => { setResolveTarget(null); setResolution(''); }} title="Resolve Escalation" size="lg">
        {resolveTarget && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg px-4 py-3">
              <p className="text-xs text-gray-500 mb-1">Query</p>
              <p className="text-sm text-gray-800">{resolveTarget.original_query}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Resolution Notes *</label>
              <textarea
                value={resolution}
                onChange={e => setResolution(e.target.value)}
                rows={4}
                placeholder="Describe how the issue was resolved..."
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100 resize-none"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={createArticle}
                onChange={e => setCreateArticle(e.target.checked)}
                className="w-4 h-4 rounded text-brand-600"
              />
              <span className="text-sm text-gray-700">Create draft article from this resolution</span>
            </label>
            <div className="flex gap-3">
              <button
                onClick={handleResolve}
                disabled={!resolution.trim() || actionLoading}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40 transition-colors"
              >
                {actionLoading ? 'Resolving…' : 'Confirm Resolution'}
              </button>
              <button
                onClick={() => { setResolveTarget(null); setResolution(''); }}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
