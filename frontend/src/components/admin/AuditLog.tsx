import React, { useState, useEffect, useCallback } from 'react';
import { Download, Filter, Lock, ChevronDown, ChevronUp } from 'lucide-react';
import { format } from 'date-fns';
import { api } from '../../services/api';
import type { AuditLog as AuditLogType } from '../../types';
import { StatusBadge } from '../shared/StatusBadge';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';

const EVENT_TYPES = [
  'QueryProcessed',
  'ArticlePublished',
  'ArticleRejected',
  'EscalationCreated',
  'EscalationResolved',
  'AccessGranted',
  'AccessDenied',
  'ActionExecuted',
  'GuardrailBlock',
  'FaithfulnessFailure',
  'ConfigurationChanged',
];

const CLASSIFICATION_TAGS = ['public', 'internal', 'confidential', 'restricted'];

export function AuditLog() {
  const [logs, setLogs] = useState<AuditLogType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    event_types: [] as string[],
    classification: '',
    from_date: '',
    to_date: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (filters.event_types.length) params['event_types'] = filters.event_types.join(',');
    if (filters.classification) params['classification'] = filters.classification;
    if (filters.from_date) params['from'] = filters.from_date;
    if (filters.to_date) params['to'] = filters.to_date;
    try {
      const data = await api.audit.list(params);
      const entries = Array.isArray(data) ? data : (data as any)?.entries ?? [];
      setLogs(entries);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const toggleEventType = (et: string) => {
    setFilters(f => ({
      ...f,
      event_types: f.event_types.includes(et)
        ? f.event_types.filter(e => e !== et)
        : [...f.event_types, et],
    }));
  };

  const exportCsv = () => {
    if (!Array.isArray(logs) || !logs.length) return;
    const headers = ['timestamp', 'event_type', 'actor_id', 'classification', 'details'];
    const rows = logs.map(l => [
      l.timestamp,
      l.event_type,
      l.actor_id ?? '',
      l.data_classification_tag,
      JSON.stringify(l.event_details).replace(/"/g, '""'),
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'audit-log.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Audit Log</h1>
            <p className="text-sm text-gray-500">Immutable append-only event record</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(f => !f)}
              className="flex items-center gap-2 px-3 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Filter size={14} /> Filters
              {(filters.event_types.length > 0 || filters.classification) && (
                <span className="w-5 h-5 rounded-full bg-brand-600 text-white text-xs flex items-center justify-center">
                  {filters.event_types.length + (filters.classification ? 1 : 0)}
                </span>
              )}
            </button>
            <button
              onClick={exportCsv}
              className="flex items-center gap-2 px-3 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Download size={14} /> Export CSV
            </button>
          </div>
        </div>

        {/* Append-only notice */}
        <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <Lock size={13} className="text-amber-600" />
          <span className="text-xs text-amber-700 font-medium">
            This log is append-only and immutable. No records can be altered or deleted. Retention: 3 years.
          </span>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-4">
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-2">Event Types</p>
              <div className="flex flex-wrap gap-2">
                {EVENT_TYPES.map(et => (
                  <label key={et} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.event_types.includes(et)}
                      onChange={() => toggleEventType(et)}
                      className="w-3.5 h-3.5 rounded text-brand-600"
                    />
                    <span className="text-xs text-gray-700">{et}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-4 flex-wrap">
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-1">Classification</p>
                <select
                  value={filters.classification}
                  onChange={e => setFilters(f => ({ ...f, classification: e.target.value }))}
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm outline-none"
                >
                  <option value="">All</option>
                  {CLASSIFICATION_TAGS.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-1">From</p>
                <input
                  type="date"
                  value={filters.from_date}
                  onChange={e => setFilters(f => ({ ...f, from_date: e.target.value }))}
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm outline-none"
                />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-1">To</p>
                <input
                  type="date"
                  value={filters.to_date}
                  onChange={e => setFilters(f => ({ ...f, to_date: e.target.value }))}
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm outline-none"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => setFilters({ event_types: [], classification: '', from_date: '', to_date: '' })}
                  className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : logs.length === 0 ? (
            <EmptyState title="No audit entries found" description="Try adjusting your filters." />
          ) : (
            <table className="min-w-full divide-y divide-gray-100">
              <thead>
                <tr className="bg-gray-50">
                  {['Timestamp', 'Event Type', 'Actor', 'Classification', 'Details'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {Array.isArray(logs) && logs.map(log => {
                  const isExpanded = expandedId === log.id;
                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                        onClick={() => setExpandedId(isExpanded ? null : log.id)}
                      >
                        <td className="px-4 py-3 text-xs text-gray-500 font-mono whitespace-nowrap">
                          {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs font-medium text-gray-800 bg-gray-100 px-2 py-0.5 rounded-md">
                            {log.event_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                          {log.actor_id ?? '—'}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={log.data_classification_tag} label={log.data_classification_tag} />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400 font-mono truncate max-w-[200px]">
                              {JSON.stringify(log.event_details).slice(0, 60)}…
                            </span>
                            {isExpanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                          </div>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="bg-gray-50">
                          <td colSpan={5} className="px-4 py-3">
                            <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap bg-gray-100 rounded-lg p-3 overflow-x-auto">
                              {JSON.stringify(log.event_details, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
