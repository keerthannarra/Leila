import { useState, useEffect } from 'react';
import { Save, Clock, Settings } from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import { useToast } from '../shared/Toast';
import { Spinner } from '../shared/Spinner';

interface ConfigEntry {
  key: string;
  label: string;
  description: string;
  defaultValue: string;
  type: 'number' | 'text';
  unit?: string;
  group: string;
}

const CONFIG_ENTRIES: ConfigEntry[] = [
  // Confidence thresholds
  { key: 'confidence_high_threshold', label: 'High Confidence Threshold', description: 'Minimum score for HIGH confidence band', defaultValue: '0.50', type: 'number', group: 'Confidence Thresholds' },
  { key: 'confidence_low_threshold', label: 'Low Confidence Threshold', description: 'Minimum score for LOW confidence band (below = NONE)', defaultValue: '0.35', type: 'number', group: 'Confidence Thresholds' },
  { key: 'faithfulness_threshold', label: 'Faithfulness Threshold', description: 'Minimum entailment score to pass faithfulness check', defaultValue: '0.85', type: 'number', group: 'Confidence Thresholds' },

  // SLA values
  { key: 'sla_escalation_hours', label: 'Escalation SLA', description: 'Hours for IT agent to respond to escalation', defaultValue: '4', type: 'number', unit: 'hours', group: 'SLA Values' },
  { key: 'sla_per_approver_hours', label: 'Per-Approver SLA', description: 'Hours for each approver in cascade to respond', defaultValue: '24', type: 'number', unit: 'hours', group: 'SLA Values' },
  { key: 'sla_aggregate_hours', label: 'Aggregate Access SLA', description: 'Maximum total hours for full access approval cascade', defaultValue: '72', type: 'number', unit: 'hours', group: 'SLA Values' },

  // Review cycles
  { key: 'review_cycle_articles_days', label: 'Article Review Cycle', description: 'Days before published articles require re-review', defaultValue: '90', type: 'number', unit: 'days', group: 'Review Cycles' },
  { key: 'review_cycle_documents_days', label: 'Document Review Cycle', description: 'Days before ingested documents require re-review', defaultValue: '90', type: 'number', unit: 'days', group: 'Review Cycles' },

  // Gap thresholds
  { key: 'gap_threshold_article', label: 'Article Gap Threshold', description: 'Occurrence count before gap cluster triggers article suggestion', defaultValue: '5', type: 'number', unit: 'occurrences', group: 'Gap Thresholds' },
  { key: 'gap_threshold_action', label: 'Action Gap Threshold', description: 'Occurrence count before gap cluster triggers action suggestion', defaultValue: '10', type: 'number', unit: 'occurrences', group: 'Gap Thresholds' },

  // Session
  { key: 'session_timeout_minutes', label: 'Session Timeout', description: 'Minutes of inactivity before chat session expires', defaultValue: '30', type: 'number', unit: 'minutes', group: 'Session' },

  // Rate limiting
  { key: 'rate_limit_queries', label: 'Rate Limit', description: 'Maximum queries allowed per user per 5-minute window', defaultValue: '60', type: 'number', unit: 'queries/5min', group: 'Rate Limiting' },
];

interface ConfigHistory {
  key: string;
  old_value: string;
  new_value: string;
  changed_by: string;
  changed_at: string;
}

export function ConfigurationConsole() {
  const { currentUser } = useRole();
  const { showToast } = useToast();
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState<ConfigHistory[]>([]);

  useEffect(() => {
    setLoading(true);
    api.config.get()
      .then(cfg => {
        setValues(cfg);
      })
      .catch(() => {
        // Use defaults when backend unavailable
        const defaults: Record<string, string> = {};
        CONFIG_ENTRIES.forEach(e => { defaults[e.key] = e.defaultValue; });
        setValues(defaults);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    const newHistory: ConfigHistory[] = [];
    try {
      for (const entry of CONFIG_ENTRIES) {
        const current = values[entry.key] ?? entry.defaultValue;
        await api.config.update(entry.key, current, currentUser.id);
        newHistory.push({
          key: entry.key,
          old_value: entry.defaultValue,
          new_value: current,
          changed_by: currentUser.name,
          changed_at: new Date().toISOString(),
        });
      }
      setHistory(prev => [...newHistory, ...prev].slice(0, 20));
      showToast('Configuration saved successfully', 'success');
    } catch {
      showToast('Failed to save some configuration values', 'error');
    } finally {
      setSaving(false);
    }
  };

  const groups = [...new Set(CONFIG_ENTRIES.map(e => e.group))];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Configuration Console</h1>
            <p className="text-sm text-gray-500">System-wide configuration parameters. All changes are logged.</p>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            <Save size={16} /> {saving ? 'Saving…' : 'Save All Changes'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {groups.map(group => (
          <div key={group} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
              <Settings size={15} className="text-brand-600" />
              <h2 className="text-sm font-semibold text-gray-800">{group}</h2>
            </div>
            <div className="divide-y divide-gray-50">
              {CONFIG_ENTRIES.filter(e => e.group === group).map(entry => (
                <div key={entry.key} className="px-5 py-4 flex items-start gap-6">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800">{entry.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{entry.description}</p>
                    <p className="text-xs text-gray-400 mt-0.5 font-mono">Default: {entry.defaultValue}{entry.unit ? ` ${entry.unit}` : ''}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <input
                      type={entry.type}
                      value={values[entry.key] ?? entry.defaultValue}
                      onChange={e => setValues(prev => ({ ...prev, [entry.key]: e.target.value }))}
                      className="w-28 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500 text-right"
                      step={entry.type === 'number' ? '0.01' : undefined}
                    />
                    {entry.unit && (
                      <span className="text-xs text-gray-400 w-20">{entry.unit}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Config change history */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
            <Clock size={15} className="text-gray-500" />
            <h2 className="text-sm font-semibold text-gray-800">Change History</h2>
          </div>
          {history.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-gray-400">
              No changes recorded in this session
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-100">
              <thead>
                <tr className="bg-gray-50">
                  {['Parameter', 'Old Value', 'New Value', 'Changed By', 'Timestamp'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((h, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs font-mono text-gray-700">{h.key}</td>
                    <td className="px-4 py-3 text-sm text-red-600 font-mono">{h.old_value}</td>
                    <td className="px-4 py-3 text-sm text-green-600 font-mono">{h.new_value}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{h.changed_by}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{format(new Date(h.changed_at), 'HH:mm:ss')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
