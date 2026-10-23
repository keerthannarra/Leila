import { Bot, User } from 'lucide-react';
import { useRole } from '../../contexts/RoleContext';
import type { Role } from '../../types';

const roleColors: Record<Role, string> = {
  employee: 'bg-blue-100 text-blue-800',
  it_support_agent: 'bg-green-100 text-green-800',
  it_content_owner: 'bg-purple-100 text-purple-800',
  it_operations_lead: 'bg-orange-100 text-orange-800',
  it_operations_manager: 'bg-red-100 text-red-800',
  resource_owner: 'bg-teal-100 text-teal-800',
  administrator: 'bg-gray-100 text-gray-800',
  compliance_reviewer: 'bg-yellow-100 text-yellow-800',
};

function formatRole(role: Role): string {
  return role.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function RoleSwitcher() {
  const { currentUser } = useRole();

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-100 shadow-sm z-30">
      {/* Logo + Title */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-brand-700 flex items-center justify-center">
          <Bot size={20} className="text-white" />
        </div>
        <div>
          <span className="text-lg font-bold text-brand-700">Leila</span>
          <span className="text-xs text-gray-400 ml-2 hidden sm:inline">IT Help Desk</span>
        </div>
      </div>

      {/* Current User Display */}
      <div className="flex items-center gap-3 px-4 py-2 rounded-lg border border-gray-200 bg-white">
        <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center">
          <User size={16} className="text-brand-700" />
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-sm font-semibold text-gray-900 leading-none mb-1">{currentUser.name}</p>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleColors[currentUser.role]}`}>
            {formatRole(currentUser.role)}
          </span>
        </div>
      </div>
    </header>
  );
}
