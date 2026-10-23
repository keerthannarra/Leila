import { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Edit2, Eye, Send, X, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { Article, CoverageGapCluster, Step } from '../../types';
import { StatusBadge } from '../shared/StatusBadge';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { EmptyState } from '../shared/EmptyState';
import { Spinner } from '../shared/Spinner';
import { Table } from '../shared/Table';

type TabKey = 'published' | 'draft' | 'pending_review' | 'retired';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'published', label: 'Published' },
  { key: 'draft', label: 'Draft' },
  { key: 'pending_review', label: 'Pending Review' },
  { key: 'retired', label: 'Retired' },
];

const CATEGORIES = ['Wi-Fi', 'Hardware', 'Software', 'Access', 'Security', 'Onboarding', 'General'];

interface ArticleFormData {
  title: string;
  content: string;
  category: string;
  context_tags: string[];
  steps: Step[];
  review_cycle_days: number;
}

const defaultForm: ArticleFormData = {
  title: '',
  content: '',
  category: 'General',
  context_tags: [],
  steps: [],
  review_cycle_days: 90,
};

function ArticleForm({
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  initial: ArticleFormData;
  onSubmit: (data: ArticleFormData) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<ArticleFormData>(initial);
  const [tagInput, setTagInput] = useState('');

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !form.context_tags.includes(t)) {
      setForm(f => ({ ...f, context_tags: [...f.context_tags, t] }));
    }
    setTagInput('');
  };

  const removeTag = (tag: string) => setForm(f => ({ ...f, context_tags: f.context_tags.filter(t => t !== tag) }));

  const addStep = () => setForm(f => ({ ...f, steps: [...f.steps, { content: '', order: f.steps.length }] }));
  const removeStep = (i: number) =>
    setForm(f => ({ ...f, steps: f.steps.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, order: idx })) }));
  const updateStep = (i: number, content: string) =>
    setForm(f => ({ ...f, steps: f.steps.map((s, idx) => (idx === i ? { ...s, content } : s)) }));

  return (
    <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
        <input
          value={form.title}
          onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500"
          placeholder="Article title"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
        <select
          value={form.category}
          onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
        >
          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Content *</label>
        <textarea
          value={form.content}
          onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
          rows={5}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100 resize-none"
          placeholder="Article content..."
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Steps (optional)</label>
        <div className="space-y-2">
          {form.steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 text-xs flex items-center justify-center font-bold flex-shrink-0 mt-1.5">
                {i + 1}
              </span>
              <input
                value={step.content}
                onChange={e => updateStep(i, e.target.value)}
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
                placeholder={`Step ${i + 1} description`}
              />
              <button onClick={() => removeStep(i)} className="text-red-400 hover:text-red-600 mt-2" aria-label="Remove step">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          <button
            onClick={addStep}
            className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
          >
            <Plus size={14} /> Add Step
          </button>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Context Tags</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {form.context_tags.map(tag => (
            <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-brand-50 text-brand-700 rounded-full text-xs font-medium">
              {tag}
              <button onClick={() => removeTag(tag)} aria-label={`Remove tag ${tag}`}>
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={tagInput}
            onChange={e => setTagInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
            placeholder="Add tag + Enter"
          />
          <button onClick={addTag} className="px-3 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors">Add</button>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Review Cycle (days)</label>
        <input
          type="number"
          value={form.review_cycle_days}
          onChange={e => setForm(f => ({ ...f, review_cycle_days: Number(e.target.value) }))}
          className="w-32 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-100"
          min={1}
        />
      </div>
      <div className="flex gap-3 pt-2 sticky bottom-0 bg-white">
        <button
          onClick={() => onSubmit(form)}
          disabled={loading || !form.title || !form.content}
          className="flex-1 bg-brand-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Saving…' : 'Save Article'}
        </button>
        <button onClick={onCancel} className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
          Cancel
        </button>
      </div>
    </div>
  );
}

export function ContentManagement() {
  const { currentUser } = useRole();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<TabKey>('published');
  const [articles, setArticles] = useState<Article[]>([]);
  const [gaps, setGaps] = useState<CoverageGapCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [viewingArticle, setViewingArticle] = useState<Article | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    try {
      const [arts, gapData] = await Promise.all([
        api.articles.list(activeTab, search || undefined),
        api.articles.coverageGaps(),
      ]);
      setArticles(arts);
      setGaps(gapData);
    } catch {
      setArticles([]);
      setGaps([]);
    } finally {
      setLoading(false);
    }
  }, [activeTab, search]);

  useEffect(() => { loadArticles(); }, [loadArticles]);

  const handleCreate = async (data: ArticleFormData) => {
    setFormLoading(true);
    try {
      await api.articles.create({ ...data, steps: data.steps.map(s => s.content), author_id: currentUser.id, author_type: 'human' });
      showToast('Article created successfully', 'success');
      setShowForm(false);
      loadArticles();
    } catch {
      showToast('Failed to create article', 'error');
    } finally {
      setFormLoading(false);
    }
  };

  const handleUpdate = async (data: ArticleFormData) => {
    if (!editingArticle) return;
    setFormLoading(true);
    try {
      await api.articles.update(editingArticle.id, { ...data, steps: data.steps.map(s => s.content), lifecycle_status: 'pending_review' });
      showToast('Article updated and submitted for review', 'success');
      setEditingArticle(null);
      loadArticles();
    } catch {
      showToast('Failed to update article', 'error');
    } finally {
      setFormLoading(false);
    }
  };

  const handleSubmit = async (article: Article) => {
    try {
      await api.articles.submit(article.id);
      showToast('Article submitted for review', 'success');
      loadArticles();
    } catch {
      showToast('Failed to submit article', 'error');
    }
  };

  const handleRetire = async (article: Article) => {
    try {
      await api.articles.retire(article.id);
      showToast('Article retired', 'info');
      loadArticles();
    } catch {
      showToast('Failed to retire article', 'error');
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Content Management</h1>
            <p className="text-sm text-gray-500">Manage knowledge base articles</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-600 transition-colors"
          >
            <Plus size={16} /> New Article
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-100">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-brand-700 text-brand-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {/* Search */}
        <div className="relative max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search articles..."
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500"
          />
        </div>

        {/* Article table */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : articles.length === 0 ? (
            <EmptyState title="No articles found" description="Create a new article or try a different filter." />
          ) : (
            <Table
              keyExtractor={a => a.id}
              data={articles}
              onRowClick={setViewingArticle}
              columns={[
                { header: 'Title', accessor: a => <span className="font-medium text-gray-900">{a.title}</span> },
                { header: 'Category', accessor: 'category' },
                { header: 'Version', accessor: a => `v${a.version}` },
                {
                  header: 'Last Reviewed',
                  accessor: a =>
                    a.last_reviewed_date
                      ? format(new Date(a.last_reviewed_date), 'MMM d, yyyy')
                      : '—',
                },
                { header: 'Status', accessor: a => <StatusBadge status={a.lifecycle_status} /> },
                {
                  header: 'Actions',
                  accessor: a => (
                    <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() => setViewingArticle(a)}
                        className="p-1.5 text-gray-400 hover:text-brand-600 rounded-lg hover:bg-brand-50 transition-colors"
                        title="View"
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        onClick={() => setEditingArticle(a)}
                        className="p-1.5 text-gray-400 hover:text-brand-600 rounded-lg hover:bg-brand-50 transition-colors"
                        title="Edit"
                      >
                        <Edit2 size={14} />
                      </button>
                      {a.lifecycle_status === 'draft' && (
                        <button
                          onClick={() => handleSubmit(a)}
                          className="p-1.5 text-gray-400 hover:text-orange-600 rounded-lg hover:bg-orange-50 transition-colors"
                          title="Submit for Review"
                        >
                          <Send size={14} />
                        </button>
                      )}
                      {a.lifecycle_status === 'published' && (
                        <button
                          onClick={() => handleRetire(a)}
                          className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                          title="Retire"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          )}
        </div>

        {/* Coverage Gaps */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-900">Coverage Gaps</h2>
            <p className="text-xs text-gray-500 mt-0.5">Unmatched user queries grouped by theme</p>
          </div>
          {gaps.length === 0 ? (
            <EmptyState title="No coverage gaps" description="All queries are being answered well." />
          ) : (
            <Table
              keyExtractor={g => g.id}
              data={gaps}
              columns={[
                { header: 'Representative Query', accessor: 'representative_query' },
                { header: 'Count', accessor: g => <span className="font-semibold text-gray-900">{g.occurrence_count}</span> },
                { header: 'Tag', accessor: g => <StatusBadge status={g.classification_tag} label={g.classification_tag} /> },
                { header: 'Status', accessor: g => <StatusBadge status={g.suggestion_status} /> },
                { header: 'First Seen', accessor: g => format(new Date(g.created_at), 'MMM d') },
              ]}
            />
          )}
        </div>
      </div>

      {/* New Article Modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title="New Article" size="lg">
        <ArticleForm
          initial={defaultForm}
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          loading={formLoading}
        />
      </Modal>

      {/* Edit Article Modal */}
      <Modal open={!!editingArticle} onClose={() => setEditingArticle(null)} title="Edit Article" size="lg">
        {editingArticle && (
          <ArticleForm
            initial={{
              title: editingArticle.title,
              content: editingArticle.content,
              category: editingArticle.category,
              context_tags: editingArticle.context_tags,
              steps: (editingArticle.steps ?? []).map((s, i) => ({ content: s, order: i })),
              review_cycle_days: editingArticle.review_cycle_days,
            }}
            onSubmit={handleUpdate}
            onCancel={() => setEditingArticle(null)}
            loading={formLoading}
          />
        )}
      </Modal>

      {/* View Article Modal */}
      <Modal open={!!viewingArticle} onClose={() => setViewingArticle(null)} title={viewingArticle?.title ?? ''} size="xl">
        {viewingArticle && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
            <div className="flex flex-wrap gap-2">
              <StatusBadge status={viewingArticle.lifecycle_status} />
              <StatusBadge status={viewingArticle.author_type} />
              <span className="text-xs text-gray-400">v{viewingArticle.version}</span>
              <span className="text-xs text-gray-400">• {viewingArticle.category}</span>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Content</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{viewingArticle.content}</p>
            </div>
            {(viewingArticle.steps ?? []).length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Troubleshooting Steps</h3>
                <ol className="space-y-2">
                  {(viewingArticle.steps ?? []).map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="w-5 h-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {viewingArticle.context_tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {viewingArticle.context_tags.map(tag => (
                  <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs">{tag}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
