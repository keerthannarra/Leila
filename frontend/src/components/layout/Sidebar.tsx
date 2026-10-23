import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  MessageSquare,
  FileText,
  CheckSquare,
  AlertTriangle,
  BarChart2,
  Shield,
  User,
  Users,
  Database,
  Zap,
  Settings,
  ScrollText,
  Eye,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import type { Role } from '../../types';

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  roles: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Chat', path: '/chat', icon: <MessageSquare size={18} />, roles: ['employee', 'it_support_agent', 'it_content_owner', 'it_operations_lead', 'it_operations_manager', 'resource_owner', 'administrator', 'compliance_reviewer'] },
  { label: 'Content Management', path: '/admin/content', icon: <FileText size={18} />, roles: ['it_content_owner', 'it_operations_manager', 'administrator'] },
  { label: 'Content Approval', path: '/admin/approvals', icon: <CheckSquare size={18} />, roles: ['it_operations_lead', 'it_operations_manager', 'administrator'] },
  { label: 'Escalation Queue', path: '/admin/escalations', icon: <AlertTriangle size={18} />, roles: ['it_support_agent', 'it_operations_manager', 'administrator'] },
  { label: 'Analytics', path: '/admin/analytics', icon: <BarChart2 size={18} />, roles: ['it_operations_lead', 'it_operations_manager', 'administrator'] },
  { label: 'Audit Log', path: '/admin/audit', icon: <ScrollText size={18} />, roles: ['it_operations_manager', 'compliance_reviewer', 'administrator'] },
  { label: 'Faithfulness Review', path: '/admin/faithfulness', icon: <Eye size={18} />, roles: ['it_operations_lead', 'compliance_reviewer', 'administrator'] },
  { label: 'Adversarial Review', path: '/admin/adversarial', icon: <Shield size={18} />, roles: ['it_operations_lead', 'administrator'] },
  { label: 'Access Requests', path: '/admin/access-requests', icon: <Users size={18} />, roles: ['resource_owner', 'it_operations_lead', 'administrator'] },
  { label: 'Action Approval', path: '/admin/actions', icon: <Zap size={18} />, roles: ['it_operations_lead', 'administrator'] },
  { label: 'Resource Catalogue', path: '/admin/resources', icon: <Database size={18} />, roles: ['administrator'] },
  { label: 'User Management', path: '/admin/users', icon: <Users size={18} />, roles: ['administrator'] },
  { label: 'Configuration', path: '/admin/config', icon: <Settings size={18} />, roles: ['administrator'] },
];

export function Sidebar() {
  const { currentUser, isAuthenticated, logout } = useAuth();
  const visibleItems = NAV_ITEMS.filter(item => 
    currentUser && item.roles.includes(currentUser.role)
  );

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  return (
    <aside className="w-56 bg-white border-r border-gray-100 flex flex-col py-4 shrink-0" aria-label="Sidebar navigation">
      <nav className="flex-1 overflow-y-auto px-3 space-y-1">
        {visibleItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-700 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>
      
      {isAuthenticated && currentUser && (
        <div className="px-4 pb-2 pt-4 border-t border-gray-100 mt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                <User size={16} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{currentUser.name}</p>
                <p className="text-xs text-gray-500">{currentUser.role.replace(/_/g, ' ').toUpperCase()}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}
      
      <div className="px-4 pb-2 pt-4 border-t border-gray-100 mt-4">
        <p className="text-xs text-gray-400">Leila v1.0</p>
        <p className="text-xs text-gray-300">AG-IT-0426-001</p>
      </div>
    </aside>
  );
}
