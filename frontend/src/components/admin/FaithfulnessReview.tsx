import { useState, useEffect } from 'react';
import { Eye, ChevronRight } from 'lucide-react';
import { format } from 'date-fns';
import { api } from '../../services/api';
import type { FaithfulnessFailure } from '../../types';
import { Spinner } from '../shared/Spinner';
import { EmptyState } from '../shared/EmptyState';

const ROOT_CAUSES = [
  'retrieval_gap',
  'embedding_drift',
  'prompt_defect',
  'true_hallucination',
];

function EntailmentBadge({ score }: { score: number }) {
  const color =
    score >= 0.85 ? 'bg-green-100 text-green-800' :
    score >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
    'bg-red-100 text-red-700';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {(score * 100).toFixed(0)}%
    </span>
  );
}

interface Claim {
  text: string;
  entailment_score: number;
}

export function FaithfulnessReview() {
  const [failures, setFailures] = useState<FaithfulnessFailure[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<FaithfulnessFailure | null>(null);
  const [rootCauses, setRootCauses] = useState<Record<string, string>>({});

  useEffect(() => {
    api.faithfulnessFailures.list()
      .then(setFailures)
      .catch(() => setFailures([]))
      .finally(() => setLoading(false));
  }, []);

  const handleRootCause = (id: string, cause: string) => {
    setRootCauses(prev => ({ ...prev, [id]: cause }));
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <h1 className="text-lg font-bold text-gray-900">Faithfulness Review</h1>
        <p className="text-sm text-gray-500">LLM answers that failed faithfulness checks</p>
        <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-400 inline-block" /> ≥85% Faithful</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-400 inline-block" /> 60-84% Partial</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-400 inline-block" /> &lt;60% Unfaithful</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto flex">
        {/* List */}
        <div className={`${selected ? 'w-1/2' : 'w-full'} px-6 py-4 transition-all`}>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-16"><Spinner /></div>
            ) : failures.length === 0 ? (
              <EmptyState
                title="No faithfulness failures"
                description="All LLM answers have passed faithfulness checks."
                icon={<Eye size={40} />}
              />
            ) : (
              <table className="min-w-full divide-y divide-gray-100">
                <thead>
                  <tr className="bg-gray-50">
                    {['Date', 'Original Query', 'Claims', 'Root Cause'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {failures.map(f => (
                    <tr
                      key={f.id}
                      onClick={() => setSelected(s => s?.id === f.id ? null : f)}
                      className={`cursor-pointer hover:bg-gray-50 transition-colors ${selected?.id === f.id ? 'bg-blue-50' : ''}`}
                    >
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                        {format(new Date(f.timestamp), 'MMM d, HH:mm')}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-800 max-w-[200px] truncate">
                        {f.original_query}
                      </td>
                      <td className="px-4 py-3 text-sm font-semibold text-gray-700">
                        {f.unsupported_claims.length}
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={rootCauses[f.id] ?? ''}
                          onChange={e => { e.stopPropagation(); handleRootCause(f.id, e.target.value); }}
                          onClick={e => e.stopPropagation()}
                          className="border border-gray-200 rounded-lg px-2 py-1 text-xs outline-none"
                        >
                          <option value="">— classify —</option>
                          {ROOT_CAUSES.map(rc => (
                            <option key={rc} value={rc}>{rc.replace(/_/g, ' ')}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="w-1/2 border-l border-gray-100 bg-white overflow-y-auto px-6 py-4 space-y-5">
            <div className="flex items-center gap-2 mb-2">
              <ChevronRight size={16} className="text-brand-500" />
              <h2 className="text-base font-semibold text-gray-900">Failure Detail</h2>
              <button
                onClick={() => setSelected(null)}
                className="ml-auto text-xs text-gray-400 hover:text-gray-600"
              >
                Close
              </button>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-semibold text-gray-500 uppercase">Original Query</p>
              <p className="text-sm text-gray-800">{selected.original_query}</p>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-semibold text-gray-500 uppercase">Suppressed LLM Answer</p>
              <p className="text-sm text-gray-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {selected.llm_answer}
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase">Unsupported Claims</p>
              {selected.unsupported_claims.length === 0 ? (
                <p className="text-sm text-gray-400">No claims flagged</p>
              ) : (
                selected.unsupported_claims.map((claim, i) => {
                  const c = claim as unknown as Claim;
                  return (
                    <div key={i} className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                      <EntailmentBadge score={c.entailment_score ?? 0} />
                      <p className="text-sm text-gray-700 flex-1">{c.text ?? JSON.stringify(c)}</p>
                    </div>
                  );
                })
              )}
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase">Retrieved Chunks ({selected.retrieved_chunks.length})</p>
              {selected.retrieved_chunks.map((chunk, i) => (
                <div key={i} className="bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
                  <p className="text-xs text-blue-700 font-mono">{JSON.stringify(chunk).slice(0, 120)}…</p>
                </div>
              ))}
            </div>

            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Root Cause Classification</p>
              <select
                value={rootCauses[selected.id] ?? ''}
                onChange={e => handleRootCause(selected.id, e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
              >
                <option value="">— Select root cause —</option>
                {ROOT_CAUSES.map(rc => (
                  <option key={rc} value={rc}>{rc.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
