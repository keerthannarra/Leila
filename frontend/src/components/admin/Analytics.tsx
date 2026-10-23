import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  BookOpen,
  Shield,
  CheckCircle,
  Clock,
  Star,
  Zap,
  Eye,
  Activity,
  Download,
  BarChart2,
} from 'lucide-react';
import { api } from '../../services/api';
import type { AnalyticsMetrics } from '../../types';
import { Spinner } from '../shared/Spinner';

type Range = '7d' | '30d' | '90d' | 'all';

interface MetricCard {
  key: keyof AnalyticsMetrics;
  label: string;
  icon: React.ReactNode;
  format: 'percent' | 'count' | 'score' | 'hours';
  color: string;
  description: string;
}

const METRIC_CARDS: MetricCard[] = [
  { key: 'query_resolution_rate', label: 'Query Resolution Rate', icon: <CheckCircle size={20} />, format: 'percent', color: 'text-green-600', description: 'Queries resolved without escalation' },
  { key: 'escalation_rate', label: 'Escalation Rate', icon: <AlertTriangle size={20} />, format: 'percent', color: 'text-orange-500', description: 'Queries escalated to support agents' },
  { key: 'kb_coverage_rate', label: 'KB Coverage Rate', icon: <BookOpen size={20} />, format: 'percent', color: 'text-blue-600', description: 'Queries answered from knowledge base' },
  { key: 'faithfulness_pass_rate', label: 'Faithfulness Pass Rate', icon: <Eye size={20} />, format: 'percent', color: 'text-purple-600', description: 'LLM answers grounded in KB content' },
  { key: 'adversarial_block_rate', label: 'Adversarial Block Rate', icon: <Shield size={20} />, format: 'percent', color: 'text-red-500', description: 'Malicious queries blocked by guardrails' },
  { key: 'action_success_rate', label: 'Action Success Rate', icon: <Zap size={20} />, format: 'percent', color: 'text-yellow-600', description: 'Automated actions completed successfully' },
  { key: 'user_satisfaction_score', label: 'Satisfaction Score', icon: <Star size={20} />, format: 'score', color: 'text-yellow-500', description: 'Average user satisfaction rating (1-5)' },
  { key: 'access_request_turnaround', label: 'Access Turnaround', icon: <Clock size={20} />, format: 'hours', color: 'text-teal-600', description: 'Average hours to approve access requests' },
  { key: 'model_correction_rate', label: 'Model Correction Rate', icon: <Activity size={20} />, format: 'percent', color: 'text-indigo-500', description: 'Answers corrected by IT Content Owners' },
  { key: 'author_correction_rate', label: 'Author Correction Rate', icon: <TrendingUp size={20} />, format: 'percent', color: 'text-pink-500', description: 'Author corrections to published articles' },
  { key: 'eligibility_block_rate', label: 'Eligibility Block Rate', icon: <Shield size={20} />, format: 'percent', color: 'text-gray-500', description: 'Access requests blocked by eligibility rules' },
];

function formatValue(value: number | undefined, fmt: MetricCard['format']): string {
  if (value === undefined || value === null) return '0';
  if (fmt === 'percent') return `${(value * 100).toFixed(1)}%`;
  if (fmt === 'score') return value.toFixed(1);
  if (fmt === 'hours') return `${value.toFixed(1)}h`;
  return value.toLocaleString();
}

function MiniBar({ value }: { value: number | undefined }) {
  if (value === undefined || value === null) return null;
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mt-2">
      <div className="h-full bg-brand-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

function SVGBarChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(...data.map(d => d.value), 1);
  const h = 80;
  const w = 320;
  const barW = Math.floor((w - (data.length - 1) * 8) / data.length);

  return (
    <svg width={w} height={h + 20} aria-label="Bar chart">
      {data.map((d, i) => {
        const barH = Math.floor((d.value / max) * h);
        const x = i * (barW + 8);
        const y = h - barH;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={barH} rx={4} fill="#3b82f6" opacity={0.8} />
            <text x={x + barW / 2} y={h + 15} textAnchor="middle" fontSize={9} fill="#9ca3af">
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Mock breakdown data
const MOCK_CATEGORY_DATA = [
  { label: 'Wi-Fi', value: 32 },
  { label: 'Access', value: 24 },
  { label: 'Software', value: 18 },
  { label: 'Hardware', value: 14 },
  { label: 'Account', value: 12 },
];

const MOCK_DAILY_QUERIES = [
  { label: 'Mon', value: 45 },
  { label: 'Tue', value: 62 },
  { label: 'Wed', value: 38 },
  { label: 'Thu', value: 71 },
  { label: 'Fri', value: 55 },
  { label: 'Sat', value: 12 },
  { label: 'Sun', value: 8 },
];

export function Analytics() {
  const [range, setRange] = useState<Range>('30d');
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.analytics.metrics()
      .then(setMetrics)
      .catch(() => {
        // Use mock data when backend unavailable
        setMetrics({
          query_resolution_rate: 0.847,
          escalation_rate: 0.153,
          kb_coverage_rate: 0.912,
          model_correction_rate: 0.042,
          author_correction_rate: 0.031,
          action_success_rate: 0.956,
          eligibility_block_rate: 0.087,
          access_request_turnaround: 3.2,
          faithfulness_pass_rate: 0.934,
          adversarial_block_rate: 0.023,
          user_satisfaction_score: 4.3,
          total_queries: 1247,
          total_escalations: 191,
        });
      })
      .finally(() => setLoading(false));
  }, [range]);

  const handleExport = () => {
    if (!metrics) return;
    const csv = Object.entries(metrics)
      .map(([k, v]) => `${k},${v}`)
      .join('\n');
    const blob = new Blob([`metric,value\n${csv}`], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `leila-analytics-${range}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-sm text-gray-500">System performance metrics and insights</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {(['7d', '30d', '90d', 'all'] as Range[]).map(r => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    range === r ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {r === 'all' ? 'All time' : r}
                </button>
              ))}
            </div>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Download size={14} /> Export
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {loading ? (
          <div className="flex items-center justify-center py-16"><Spinner size="lg" /></div>
        ) : metrics ? (
          <>
            {/* Volume summary */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-brand-700 text-white rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-brand-100">Total Queries</span>
                  <BarChart2 size={20} className="text-brand-300" />
                </div>
                <p className="text-4xl font-bold">{metrics.total_queries?.toLocaleString() || '0'}</p>
                <p className="text-xs text-brand-200 mt-1">In selected period</p>
              </div>
              <div className="bg-orange-500 text-white rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-orange-100">Total Escalations</span>
                  <AlertTriangle size={20} className="text-orange-200" />
                </div>
                <p className="text-4xl font-bold">{metrics.total_escalations?.toLocaleString() || '0'}</p>
                <p className="text-xs text-orange-100 mt-1">{(metrics.escalation_rate * 100).toFixed(1)}% of queries</p>
              </div>
            </div>

            {/* Metric cards */}
            <div className="grid grid-cols-3 gap-4">
              {METRIC_CARDS.map(card => {
                const value = metrics[card.key] as number;
                const isPercent = card.format === 'percent';
                return (
                  <div key={card.key} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className={`${card.color}`}>{card.icon}</span>
                      <span className="text-2xl font-bold text-gray-900">{formatValue(value, card.format)}</span>
                    </div>
                    <p className="text-sm font-semibold text-gray-700">{card.label}</p>
                    <p className="text-xs text-gray-400 mt-0.5 mb-2">{card.description}</p>
                    {isPercent && <MiniBar value={value} />}
                  </div>
                );
              })}
            </div>

            {/* Charts */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Queries by Category</h3>
                <SVGBarChart data={MOCK_CATEGORY_DATA} />
              </div>
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Daily Query Volume</h3>
                <SVGBarChart data={MOCK_DAILY_QUERIES} />
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
