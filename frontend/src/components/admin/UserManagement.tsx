import { useState, useEffect } from 'react';
import { Plus, Users } from 'lucide-react';
import { api } from '../../services/api';
import type { User, Role } from '../../types';
import { StatusBadge } from '../shared/StatusBadge';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';
import { Table } from '../shared/Table';

const ROLES: Role[] = [
  'employee',
  'it_support_agent',
  'it_content_owner',
  'it_operations_lead',
  'it_operations_manager',
  'resource_owner',
  'administrator',
  'compliance_reviewer',
];

interface UserForm {
  name: string;
  email: string;
  role: Role;
  employment_type: string;
}

const defaultForm: UserForm = {
  name: '',
  email: '',
  role: 'employee',
  employment_type: 'full_time',
};

export function UserManagement() {
  const { showToast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<UserForm>(defaultForm);
  const [formLoading, setFormLoading] = useState(false);

  const load = () => {
    setLoading(true);
    api.users.list()
      .then(setUsers)
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim() || !form.email.trim()) return;
    setFormLoading(true);
    try {
      await api.users.create(form);
      showToast('User created successfully', 'success');
      setShowForm(false);
      setForm(defaultForm);
      load();
    } catch {
      showToast('Failed to create user', 'error');
    } finally {
      setFormLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">User Management</h1>
            <p className="text-sm text-gray-500">Manage users and role assignments</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-600 transition-colors"
          >
            <Plus size={16} /> New User
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : users.length === 0 ? (
            <EmptyState title="No users found" icon={<Users size={40} />} />
          ) : (
            <Table
              keyExtractor={u => u.id}
              data={users}
              columns={[
                { header: 'Name', accessor: u => <span className="font-medium text-gray-900">{u.name}</span> },
                { header: 'Email', accessor: u => <span className="font-mono text-xs text-gray-500">{u.email}</span> },
                { header: 'Role', accessor: u => <StatusBadge status={u.role} label={u.role.replace(/_/g, ' ')} /> },
                { header: 'Employment Type', accessor: u => <span className="text-sm text-gray-500 capitalize">{u.employment_type?.replace(/_/g, ' ') ?? '—'}</span> },
                { header: 'Manager', accessor: u => <span className="text-xs text-gray-400 font-mono">{u.manager_id ?? '—'}</span> },
              ]}
            />
          )}
        </div>
      </div>

      <Modal open={showForm} onClose={() => { setShowForm(false); setForm(defaultForm); }} title="New User">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
              placeholder="Jane Smith"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
              placeholder="jane@company.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <select
              value={form.role}
              onChange={e => setForm(f => ({ ...f, role: e.target.value as Role }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none"
            >
              {ROLES.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Employment Type</label>
            <select
              value={form.employment_type}
              onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none"
            >
              <option value="full_time">Full Time</option>
              <option value="part_time">Part Time</option>
              <option value="contractor">Contractor</option>
              <option value="intern">Intern</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleCreate}
              disabled={formLoading || !form.name.trim() || !form.email.trim()}
              className="flex-1 bg-brand-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-40 transition-colors"
            >
              {formLoading ? 'Creating…' : 'Create User'}
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
