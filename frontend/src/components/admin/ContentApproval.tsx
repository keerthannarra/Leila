import { useState, useEffect, useCallback } from 'react';
import { Check, X, Upload, FileText } from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { Article } from '../../types';
import { StatusBadge } from '../shared/StatusBadge';
import { Modal } from '../shared/Modal';
import { useToast } from '../shared/Toast';
import { EmptyState } from '../shared/EmptyState';
import { Spinner } from '../shared/Spinner';

type Tab = 'articles' | 'documents';

export function ContentApproval() {
  const { currentUser } = useRole();
  const { showToast } = useToast();
  const [tab, setTab] = useState<Tab>('articles');
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<Article | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const loadPending = useCallback(async () => {
    setLoading(true);
    try {
      const arts = await api.articles.list('pending_review');
      setArticles(arts);
    } catch {
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPending(); }, [loadPending]);

  const handleApprove = async (article: Article) => {
    if (article.author_id === currentUser.id) return;
    setActionLoading(article.id);
    try {
      await api.articles.approve(article.id, currentUser.id);
      showToast(`"${article.title}" approved and published`, 'success');
      loadPending();
    } catch {
      showToast('Failed to approve article', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!rejectTarget || !rejectReason.trim()) return;
    setActionLoading(rejectTarget.id);
    try {
      await api.articles.reject(rejectTarget.id, currentUser.id, rejectReason);
      showToast(`"${rejectTarget.title}" rejected`, 'error');
      setRejectTarget(null);
      setRejectReason('');
      loadPending();
    } catch {
      showToast('Failed to reject article', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setUploading(true);
    try {
      await api.articles.uploadDocument(uploadFile, currentUser.id);
      showToast('Document uploaded for ingestion', 'success');
      setUploadFile(null);
    } catch {
      showToast('Upload failed', 'error');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-6 py-4">
        <h1 className="text-lg font-bold text-gray-900">Content Approval</h1>
        <p className="text-sm text-gray-500">Review and approve knowledge base submissions</p>

        <div className="flex gap-1 mt-4 border-b border-gray-100">
          {(['articles', 'documents'] as Tab[]).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 capitalize transition-colors ${
                tab === t ? 'border-brand-700 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'articles' ? <span className="flex items-center gap-1.5"><FileText size={14} />Articles ({articles.length})</span> : <span className="flex items-center gap-1.5"><Upload size={14} />Documents</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {tab === 'articles' ? (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-16"><Spinner /></div>
            ) : articles.length === 0 ? (
              <EmptyState title="No articles pending review" description="All articles have been reviewed." />
            ) : (
              <table className="min-w-full divide-y divide-gray-100">
                <thead>
                  <tr className="bg-gray-50">
                    {['Title', 'Category', 'Author', 'Author Type', 'Submitted', 'Actions'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {articles.map(article => {
                    const isSelfAuthored = article.author_id === currentUser.id;
                    return (
                      <tr key={article.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{article.title}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{article.category}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{article.author_id}</td>
                        <td className="px-4 py-3">
                          <StatusBadge
                            status={article.author_type}
                            label={article.author_type === 'agent_drafted' ? 'Agent Drafted' : 'Human'}
                          />
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {format(new Date(article.updated_at), 'MMM d, yyyy')}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="relative group">
                              <button
                                onClick={() => handleApprove(article)}
                                disabled={isSelfAuthored || actionLoading === article.id}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                              >
                                <Check size={13} /> Approve
                              </button>
                              {isSelfAuthored && (
                                <div className="absolute bottom-full mb-1 left-0 w-44 bg-gray-800 text-white text-xs rounded-lg px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                                  Cannot self-approve
                                </div>
                              )}
                            </div>
                            <button
                              onClick={() => setRejectTarget(article)}
                              disabled={actionLoading === article.id}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 text-xs font-medium rounded-lg hover:bg-red-100 transition-colors disabled:opacity-40"
                            >
                              <X size={13} /> Reject
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8">
            <h2 className="text-base font-semibold text-gray-900 mb-2">Upload Document</h2>
            <p className="text-sm text-gray-500 mb-4">
              Upload PDF, Word, Excel, or PowerPoint files for ingestion into the knowledge base.
            </p>
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-brand-300 transition-colors">
              <Upload size={32} className="text-gray-300 mx-auto mb-3" />
              <label className="cursor-pointer">
                <span className="text-sm font-medium text-brand-600 hover:text-brand-700">Choose a file</span>
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xlsx,.csv,.pptx"
                  onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
                />
              </label>
              <p className="text-xs text-gray-400 mt-1">PDF, Word, Excel, PPT up to 50MB</p>
              {uploadFile && (
                <p className="text-sm text-gray-700 mt-3 font-medium">{uploadFile.name}</p>
              )}
            </div>
            {uploadFile && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="mt-4 w-full bg-brand-700 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-40 transition-colors"
              >
                {uploading ? 'Uploading…' : 'Upload & Ingest'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Reject Modal */}
      <Modal open={!!rejectTarget} onClose={() => { setRejectTarget(null); setRejectReason(''); }} title="Reject Article">
        {rejectTarget && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Rejecting: <span className="font-semibold">{rejectTarget.title}</span>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Rejection Reason *</label>
              <textarea
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                rows={3}
                placeholder="Provide reason for rejection..."
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-red-100 resize-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleReject}
                disabled={!rejectReason.trim() || !!actionLoading}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-40 transition-colors"
              >
                Confirm Reject
              </button>
              <button
                onClick={() => { setRejectTarget(null); setRejectReason(''); }}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
