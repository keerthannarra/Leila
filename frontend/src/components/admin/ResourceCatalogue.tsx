import { useState, useEffect, useCallback } from 'react';
import { Plus, Database, AlertTriangle, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { Resource } from '../../types';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';

const CATEGORIES = ['Drive', 'VPN', 'Software', 'Hardware', 'Database', 'Admin', 'Other'];

const defaultCascade = { approver_type: 'manager', scope: 'team' };

interface ResourceForm {
  name: string;
  category: string;
  owner_ids: string[];
  eligibility_rule: string;
  approval_cascade: typeof defaultCascade[];
}

export function ResourceCatalogue() {
  const { currentUser } = useRole();
  const { showToast } = useToast();
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [form, setForm] = useState<ResourceForm>({
    name: '',
    category: 'Drive',
    owner_ids: [currentUser.id],
    eligibility_rule: '{}',
    approval_cascade: [{ ...defaultCascade }],
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.resources.list();
      setResources(data);
    } catch {
      setResources([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const addCascadeEntry = () => {
    if (form.approval_cascade.length >= 3) return;
    setForm(f => ({ ...f, approval_cascade: [...f.approval_cascade, { ...defaultCascade }] }));
  };

  const removeCascadeEntry = (i: number) => {
    setForm(f => ({ ...f, approval_cascade: f.approval_cascade.filter((_, idx) => idx !== i) }));
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    let eligibility: Record<string, unknown> = {};
    try { eligibility = JSON.parse(form.eligibility_rule); } catch { showToast('Invalid eligibility rule JSON', 'error'); return; }
    setFormLoading(true);
    try {
      await api.resources.create({
        name: form.name,
        category: form.category,
        owner_ids: form.owner_ids,
        eligibility_rule: eligibility,
        approval_cascade: form.approval_cascade,
      });
      showToast('Resource created successfully', 'success');
      setShowForm(false);
      load();
    } catch {
      showToast('Failed to create resource', 'error');
    } finally {
      setFormLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Resource Catalogue</h1>
            <p className="text-sm text-gray-500">Define and manage requestable IT resources</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-600 transition-colors"
          >
            <Plus size={16} /> New Resource
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-16"><Spinner /></div>
        ) : resources.length === 0 ? (
          <EmptyState
            title="No resources defined"
            description="Create your first resource to enable access requests."
            icon={<Database size={40} />}
          />
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {resources.map(res => (
              <div key={res.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{res.name}</h3>
                    <span className="text-xs text-gray-500 capitalize">{res.category}</span>
                  </div>
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
                    {res.approval_cascade.length} approver{res.approval_cascade.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-gray-500">
                  <p><span className="font-medium">Owners:</span> {res.owner_ids.join(', ')}</p>
                  <p><span className="font-medium">Cascade depth:</span> {res.approval_cascade.length}/3</p>
                  {res.approval_cascade.length >= 3 && (
                    <div className="flex items-center gap-1 text-amber-600">
                      <AlertTriangle size={11} />
                      <span>Maximum cascade depth reached</span>
                    </div>
                  )}
                  <p className="text-gray-400">Created {format(new Date(res.created_at), 'MMM d, yyyy')}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal open={showForm} onClose={() => setShowForm(false)} title="New Resource" size="lg">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Resource Name *</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
              placeholder="e.g., Engineering Drive, VPN Access"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              value={form.category}
              onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none"
            >
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Eligibility Rule (JSON)</label>
            <textarea
              value={form.eligibility_rule}
              onChange={e => setForm(f => ({ ...f, eligibility_rule: e.target.value }))}
              rows={3}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-brand-100 resize-none"
              placeholder='{ "role": ["employee", "contractor"] }'
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">
                Approval Cascade ({form.approval_cascade.length}/3)
              </label>
              <button
                onClick={addCascadeEntry}
                disabled={form.approval_cascade.length >= 3}
                className="text-xs text-brand-600 font-medium hover:text-brand-700 disabled:opacity-40"
              >
                + Add Approver
              </button>
            </div>
            {form.approval_cascade.length >= 3 && (
              <div className="flex items-center gap-1 text-amber-600 text-xs mb-2">
                <AlertTriangle size={12} />
                <span>Maximum cascade depth (3) reached</span>
              </div>
            )}
            <div className="space-y-2">
              {form.approval_cascade.map((entry, i) => (
                <div key={i} className="flex items-center gap-2 bg-gray-50 rounded-lg p-3">
                  <span className="text-xs font-semibold text-gray-500 w-16 flex-shrink-0">Level {i + 1}</span>
                  <select
                    value={entry.approver_type}
                    onChange={e => setForm(f => ({
                      ...f,
                      approval_cascade: f.approval_cascade.map((a, idx) => idx === i ? { ...a, approver_type: e.target.value } : a),
                    }))}
                    className="flex-1 border border-gray-200 rounded-lg px-2 py-1.5 text-xs outline-none"
                  >
                    <option value="manager">Manager</option>
                    <option value="it_ops_lead">IT Ops Lead</option>
                    <option value="resource_owner">Resource Owner</option>
                  </select>
                  <button onClick={() => removeCascadeEntry(i)} className="text-red-400 hover:text-red-600" aria-label="Remove">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleCreate}
              disabled={formLoading || !form.name.trim()}
              className="flex-1 bg-brand-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-40 transition-colors"
            >
              {formLoading ? 'Creating…' : 'Create Resource'}
            </button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
