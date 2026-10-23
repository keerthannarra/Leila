import { useState, useEffect, useCallback } from 'react';
import { Plus, Zap, Check } from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { AutomatedAction } from '../../types';
import { StatusBadge } from '../shared/StatusBadge';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';
import { Table } from '../shared/Table';

type Tab = 'all' | 'pending';

interface ActionForm {
  name: string;
  description: string;
  parameter_schema: string;
  eligibility_rule: string;
  approval_required: boolean;
}

const defaultForm: ActionForm = {
  name: '',
  description: '',
  parameter_schema: '{\n  "type": "object",\n  "properties": {}\n}',
  eligibility_rule: '{}',
  approval_required: true,
};

export function ActionManagement() {
  const { currentUser } = useRole();
  const { showToast } = useToast();
  const [tab, setTab] = useState<Tab>('all');
  const [actions, setActions] = useState<AutomatedAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [form, setForm] = useState<ActionForm>(defaultForm);
  const [approveLoading, setApproveLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const status = tab === 'pending' ? 'pending_approval' : undefined;
      const data = await api.actions.list(status);
      setActions(data);
    } catch {
      setActions([]);
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    let paramSchema: Record<string, unknown> = {};
    let eligRule: Record<string, unknown> = {};
    try { paramSchema = JSON.parse(form.parameter_schema); } catch { showToast('Invalid parameter schema JSON', 'error'); return; }
    try { eligRule = JSON.parse(form.eligibility_rule); } catch { showToast('Invalid eligibility rule JSON', 'error'); return; }
    if (!form.name.trim()) return;

    setFormLoading(true);
    try {
      await api.actions.create({
        name: form.name,
        description: form.description,
        parameter_schema: paramSchema,
        eligibility_rule: eligRule,
        approval_required: form.approval_required,
        author_id: currentUser.id,
      });
      showToast('Action created and submitted for review', 'success');
      setShowForm(false);
      setForm(defaultForm);
      load();
    } catch {
      showToast('Failed to create action', 'error');
    } finally {
      setFormLoading(false);
    }
  };

  const handleApprove = async (action: AutomatedAction) => {
    if (action.author_id === currentUser.id) {
      showToast('Cannot self-approve an action', 'error');
      return;
    }
    setApproveLoading(action.id);
    try {
      await api.actions.approve(action.id, currentUser.id);
      showToast(`"${action.name}" approved`, 'success');
      load();
    } catch {
      showToast('Failed to approve action', 'error');
    } finally {
      setApproveLoading(null);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Action Management</h1>
            <p className="text-sm text-gray-500">Create and approve automated IT actions</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-600 transition-colors"
          >
            <Plus size={16} /> New Action
          </button>
        </div>

        <div className="flex gap-1">
          {([['all', 'All Actions'], ['pending', 'Pending Approval']] as [Tab, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === key ? 'border-brand-700 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : actions.length === 0 ? (
            <EmptyState
              title={tab === 'pending' ? 'No actions pending approval' : 'No actions found'}
              description="Create a new automated action to get started."
              icon={<Zap size={40} />}
            />
          ) : (
            <Table
              keyExtractor={a => a.id}
              data={actions}
              columns={[
                { header: 'Name', accessor: a => <span className="font-medium text-gray-900">{a.name}</span> },
                { header: 'Description', accessor: a => <span className="text-gray-500 text-sm truncate block max-w-xs">{a.description}</span> },
                { header: 'Approval Required', accessor: a => <span className={`text-xs font-medium ${a.approval_required ? 'text-orange-600' : 'text-green-600'}`}>{a.approval_required ? 'Yes' : 'No'}</span> },
                { header: 'Status', accessor: a => <StatusBadge status={a.lifecycle_status} /> },
                { header: 'Author', accessor: a => <span className="font-mono text-xs text-gray-500">{a.author_id}</span> },
                { header: 'Created', accessor: a => format(new Date(a.created_at), 'MMM d, yyyy') },
                {
                  header: 'Actions',
                  accessor: a => {
                    const isSelfAuthored = a.author_id === currentUser.id;
                    const isPending = a.lifecycle_status === 'pending_approval';
                    if (!isPending) return <span className="text-xs text-gray-400">—</span>;
                    return (
                      <div className="relative group">
                        <button
                          onClick={() => handleApprove(a)}
                          disabled={isSelfAuthored || approveLoading === a.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          <Check size={13} /> Approve
                        </button>
                        {isSelfAuthored && (
                          <div className="absolute bottom-full mb-1 left-0 w-40 bg-gray-800 text-white text-xs rounded-lg px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                            Cannot self-approve
                          </div>
                        )}
                      </div>
                    );
                  },
                },
              ]}
            />
          )}
        </div>
      </div>

      {/* Create Action Modal */}
      <Modal open={showForm} onClose={() => { setShowForm(false); setForm(defaultForm); }} title="New Automated Action" size="xl">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Action Name *</label>
              <input
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
                placeholder="e.g., provision_vpn_access"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.approval_required}
                  onChange={e => setForm(f => ({ ...f, approval_required: e.target.checked }))}
                  className="w-4 h-4 rounded text-brand-600"
                />
                <span className="text-sm text-gray-700">Requires Approval</span>
              </label>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={2}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100 resize-none"
              placeholder="Describe what this action does and when it should be triggered..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Parameter Schema (JSON Schema)</label>
            <textarea
              value={form.parameter_schema}
              onChange={e => setForm(f => ({ ...f, parameter_schema: e.target.value }))}
              rows={6}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-brand-100 resize-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Eligibility Rule (JSON)</label>
            <textarea
              value={form.eligibility_rule}
              onChange={e => setForm(f => ({ ...f, eligibility_rule: e.target.value }))}
              rows={3}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-brand-100 resize-none"
              placeholder='{ "role": { "not": "intern" } }'
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleCreate}
              disabled={formLoading || !form.name.trim()}
              className="flex-1 bg-brand-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-40 transition-colors"
            >
              {formLoading ? 'Creating…' : 'Create & Submit for Review'}
            </button>
            <button
              onClick={() => { setShowForm(false); setForm(defaultForm); }}
              className="px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
