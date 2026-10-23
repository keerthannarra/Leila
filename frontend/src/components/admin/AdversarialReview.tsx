import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Settings } from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { GuardrailBlock } from '../../types';
import { Modal } from '../shared/Modal';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';
import { useToast } from '../shared/Toast';

export function AdversarialReview() {
  const { currentRole } = useRole();
  const { showToast } = useToast();
  const [blocks, setBlocks] = useState<GuardrailBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPatternModal, setShowPatternModal] = useState(false);
  const [patternDict, setPatternDict] = useState('');
  const isAdmin = currentRole === 'administrator';

  useEffect(() => {
    api.guardrailBlocks.list()
      .then(setBlocks)
      .catch(() => setBlocks([]))
      .finally(() => setLoading(false));
  }, []);

  const thisMonth = blocks.filter(b => {
    const d = new Date(b.timestamp);
    const now = new Date();
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  });

  const handleSavePatterns = () => {
    try {
      JSON.parse(patternDict);
      showToast('Pattern dictionary updated', 'success');
      setShowPatternModal(false);
    } catch {
      showToast('Invalid JSON format', 'error');
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Adversarial Review</h1>
            <p className="text-sm text-gray-500">Monitor and review guardrail-blocked queries</p>
          </div>
          {isAdmin && (
            <button
              onClick={() => setShowPatternModal(true)}
              className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Settings size={14} /> Update Pattern Dictionary
            </button>
          )}
        </div>

        {/* Monthly indicator */}
        <div className="mt-4 flex items-center gap-4">
          <div className="flex items-center gap-3 bg-orange-50 border border-orange-200 rounded-xl px-4 py-3">
            <AlertTriangle size={20} className="text-orange-500" />
            <div>
              <p className="text-2xl font-bold text-orange-700">{thisMonth.length}</p>
              <p className="text-xs text-orange-600">blocks this month</p>
            </div>
          </div>
          <div className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
            <Shield size={20} className="text-gray-500" />
            <div>
              <p className="text-2xl font-bold text-gray-700">{blocks.length}</p>
              <p className="text-xs text-gray-500">total blocks recorded</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : blocks.length === 0 ? (
            <EmptyState
              title="No guardrail blocks"
              description="No adversarial queries have been blocked."
              icon={<Shield size={40} />}
            />
          ) : (
            <table className="min-w-full divide-y divide-gray-100">
              <thead>
                <tr className="bg-gray-50">
                  {['Date', 'User', 'Blocked Query', 'Matched Pattern', 'Block Reason'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {blocks.map(block => (
                  <tr key={block.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {format(new Date(block.timestamp), 'MMM d, HH:mm')}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-500">
                      {block.user_id ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-800 max-w-xs">
                      <span title={block.blocked_query}>
                        {block.blocked_query.slice(0, 80)}{block.blocked_query.length > 80 ? '…' : ''}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded font-mono">
                        {block.matched_pattern}
                      </code>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {block.block_reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Pattern Dictionary Modal */}
      <Modal
        open={showPatternModal}
        onClose={() => setShowPatternModal(false)}
        title="Update Pattern Dictionary"
        size="lg"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Define guardrail patterns as a JSON object. Each key is a pattern name, value is the regex.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pattern Dictionary (JSON)</label>
            <textarea
              value={patternDict}
              onChange={e => setPatternDict(e.target.value)}
              rows={10}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-brand-100 resize-none"
              placeholder={`{\n  "prompt_injection": "ignore.*instructions",\n  "system_override": "you are now",\n  "jailbreak": "DAN|do anything now"\n}`}
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleSavePatterns}
              className="flex-1 bg-brand-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-600 transition-colors"
            >
              Save Patterns
            </button>
            <button
              onClick={() => setShowPatternModal(false)}
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
