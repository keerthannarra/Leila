

type BadgeVariant =
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'retired'
  | 'open'
  | 'in_progress'
  | 'resolved'
  | 'high'
  | 'low'
  | 'none'
  | 'human'
  | 'agent_drafted'
  | 'active'
  | 'inactive'
  | string;

const variantClasses: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending_review: 'bg-yellow-100 text-yellow-800',
  published: 'bg-green-100 text-green-800',
  retired: 'bg-red-100 text-red-700',
  open: 'bg-red-100 text-red-700',
  in_progress: 'bg-blue-100 text-blue-700',
  resolved: 'bg-green-100 text-green-800',
  high: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  none: 'bg-red-100 text-red-700',
  human: 'bg-blue-100 text-blue-800',
  agent_drafted: 'bg-orange-100 text-orange-800',
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-600',
};

interface StatusBadgeProps {
  status: BadgeVariant;
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const classes = variantClasses[status] ?? 'bg-gray-100 text-gray-700';
  const text = label ?? status.replace(/_/g, ' ');
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${classes}`}>
      {text}
    </span>
  );
}
