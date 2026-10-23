import { useState, useEffect, useCallback } from 'react';
import { Clock, Check, X } from 'lucide-react';
import { differenceInHours } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { AccessRequest } from '../../types';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';

function SlaTimer({ deadline }: { deadline: string }) {
  const remaining = differenceInHours(new Date(deadline), new Date());
  const isBreached = remaining <= 0;
  const isWarning = remaining <= 2 && !isBreached;
  return (
    <span className={`flex items-center gap-1 text-xs font-medium ${
      isBreached ? 'text-red-600' : isWarning ? 'text-yellow-600' : 'text-gray-500'
    }`}>
      <Clock size={11} />
      {isBreached ? `Overdue by ${Math.abs(remaining)}h` : `${remaining}h left`}
    </span>
  );
}

export function AccessRequestQueue() {
  const { currentUser } = useRole();
  const { showToast } = useToast();
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<AccessRequest | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.accessRequests.list(statusFilter || undefined);
      setRequests(data);
    } catch {
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async (req: AccessRequest) => {
    setActionLoading(req.id);
    try {
      await api.accessRequests.approve(req.id, currentUser.id);
      showToast('Access request approved', 'success');
      load();
    } catch {
      showToast('Failed to approve request', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!rejectTarget || !rejectReason.trim()) return;
    setActionLoading(rejectTarget.id);
    try {
      await api.accessRequests.reject(rejectTarget.id, currentUser.id, rejectReason);
      showToast('Access request rejected', 'error');
      setRejectTarget(null);
      setRejectReason('');
      load();
    } catch {
      showToast('Failed to reject request', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const cascadePosition = (req: AccessRequest) => {
    const done = req.approval_history.length;
    return `${done + 1} of ?`;
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Access Request Queue</h1>
            <p className="text-sm text-gray-500">Review and approve resource access requests</p>
          </div>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : requests.length === 0 ? (
            <EmptyState title="No access requests" description="No requests match the current filter." />
          ) : (
            <table className="min-w-full divide-y divide-gray-100">
              <thead>
                <tr className="bg-gray-50">
                  {['Resource', 'Requester', 'Reason', 'Cascade Position', 'SLA', 'History', 'Actions'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {requests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{req.resource_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 font-mono">{req.requester_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">{req.reason}</td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-mono text-gray-600">{cascadePosition(req)}</span>
                    </td>
                    <td className="px-4 py-3">
                      <SlaTimer deadline={req.sla_deadline} />
                    </td>
                    <td className="px-4 py-3">
                      {req.approval_history.length === 0 ? (
                        <span className="text-xs text-gray-400">No history</span>
                      ) : (
                        <div className="space-y-1">
                          {req.approval_history.slice(-2).map((h, i) => (
                            <div key={i} className="flex items-center gap-1.5">
                              <span className={`w-2 h-2 rounded-full ${h.decision === 'approved' ? 'bg-green-400' : 'bg-red-400'}`} />
                              <span className="text-xs text-gray-500">{h.approver_id} — {h.decision}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApprove(req)}
                          disabled={!!actionLoading}
                          className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 disabled:opacity-40 transition-colors"
                        >
                          <Check size={12} /> Approve
                        </button>
                        <button
                          onClick={() => setRejectTarget(req)}
                          disabled={!!actionLoading}
                          className="flex items-center gap-1 px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 text-xs font-medium rounded-lg hover:bg-red-100 disabled:opacity-40 transition-colors"
                        >
                          <X size={12} /> Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      <Modal open={!!rejectTarget} onClose={() => { setRejectTarget(null); setRejectReason(''); }} title="Reject Access Request">
        {rejectTarget && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-700">
              <p><span className="font-medium">Resource:</span> {rejectTarget.resource_id}</p>
              <p><span className="font-medium">Requester:</span> {rejectTarget.requester_id}</p>
              <p><span className="font-medium">Reason:</span> {rejectTarget.reason}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Rejection Reason *</label>
              <textarea
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                rows={3}
                placeholder="Explain the rejection..."
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-red-100 resize-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleReject}
                disabled={!rejectReason.trim() || !!actionLoading}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-40 transition-colors"
              >
                Confirm Reject
              </button>
              <button
                onClick={() => { setRejectTarget(null); setRejectReason(''); }}
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
