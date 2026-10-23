import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Bot,
  Send,
  Copy,
  CheckCheck,
  Star,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  CheckCircle2,
  MessageSquarePlus,
  MessageSquare,
} from 'lucide-react';
import { format } from 'date-fns';
import { useRole } from '../../contexts/RoleContext';
import { api } from '../../services/api';
import type { ChatMessage, ChatResponse } from '../../types';

interface MessageMeta {
  confidence_band?: 'HIGH' | 'LOW' | 'NONE';
  session_id?: string;
  interaction_id?: string;
  escalated?: boolean;
  jira_reference?: string;
  step_index?: number;     // current step index (0-based), set during troubleshooting flow
  total_steps?: number;    // total steps in the article
  needs_rating?: boolean;  // prompt user for satisfaction rating
  ask_relevance?: boolean; // LOW confidence — ask if article is relevant
  options?: string[];      // For rendering clickable quick replies
}


interface SessionData {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3">
      <div className="w-8 h-8 rounded-full bg-brand-700 flex items-center justify-center flex-shrink-0">
        <Bot size={16} className="text-white" />
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1.5 items-center h-4">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

function StarRating({ onRate }: { onRate: (n: number) => void }) {
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);

  const handleClick = (n: number) => {
    setSelected(n);
    onRate(n);
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      <span className="text-xs text-gray-500 mr-1">Rate this answer:</span>
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          onClick={() => handleClick(n)}
          onMouseEnter={() => setHovered(n)}
          onMouseLeave={() => setHovered(0)}
          className="transition-transform hover:scale-110"
          aria-label={`Rate ${n} star${n > 1 ? 's' : ''}`}
          disabled={selected > 0}
        >
          <Star
            size={18}
            className={n <= (hovered || selected) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}
          />
        </button>
      ))}
      {selected > 0 && <span className="text-xs text-green-600 ml-2">Thanks for your feedback!</span>}
    </div>
  );
}

function EscalationCard({ jiraRef }: { jiraRef?: string }) {
  return (
    <div className="mt-3 bg-orange-50 border border-orange-200 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <AlertCircle size={16} className="text-orange-500" />
        <span className="text-sm font-semibold text-orange-800">Escalated to IT Support</span>
      </div>
      {jiraRef && (
        <div className="flex items-center gap-2 text-xs text-orange-700">
          <ExternalLink size={12} />
          <span>JIRA: <span className="font-mono font-semibold">{jiraRef}</span></span>
        </div>
      )}
      <p className="text-xs text-orange-600 mt-1">Expected response time: 4 business hours</p>
    </div>
  );
}

export function ChatInterface() {
  const { currentUser } = useRole();
  const activeSessionKey = `leila_active_session_${currentUser.id}`;
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [messages, setMessages] = useState<(ChatMessage & { meta?: MessageMeta })[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [backendDown, setBackendDown] = useState(false);
  const [copied, setCopied] = useState(false);
  const [ratedIds, setRatedIds] = useState<Set<string>>(new Set());
  const [resolvedMsgIds, setResolvedMsgIds] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await api.chat.getSessions(currentUser.id);
      setSessions(data);
    } catch (e) {
      // ignore
    }
  }, [currentUser.id]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const loadNewChat = useCallback(() => {
    localStorage.removeItem(activeSessionKey);
    setSessionId(undefined);
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: `Hi ${currentUser.name.split(' ')[0]}! I'm Leila, your IT Help Desk assistant. What can I help you with today?`,
        timestamp: new Date().toISOString(),
        type: 'answer',
        meta: {
          options: [
            'Wi-Fi and network issues',
            'Software installation and configuration',
            'Access requests and provisioning',
            'Hardware troubleshooting',
            'Account and password issues'
          ]
        }
      },
    ]);
  }, [activeSessionKey, currentUser.name]);

  const loadSessionHistory = useCallback(async (sid: string) => {
    setSessionId(sid);
    localStorage.setItem(activeSessionKey, sid);
    setIsLoading(true);
    try {
      const data = await api.chat.getSessionHistory(sid);
      if (data && data.messages) {
        setMessages(data.messages as any);
      }
    } catch (e) {
      console.error(e);
      localStorage.removeItem(activeSessionKey);
      loadNewChat();
    } finally {
      setIsLoading(false);
    }
  }, [activeSessionKey, loadNewChat]);

  useEffect(() => {
    const savedSessionId = localStorage.getItem(activeSessionKey);
    if (savedSessionId) {
      loadSessionHistory(savedSessionId);
    } else {
      loadNewChat();
    }
  }, [activeSessionKey, loadNewChat, loadSessionHistory]);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const addMessage = useCallback((msg: ChatMessage & { meta?: MessageMeta }) => {
    setMessages(prev => [...prev, msg]);
  }, []);

  const handleSend = useCallback(async (overrideQuery?: string | React.MouseEvent | React.KeyboardEvent) => {
    const query = (typeof overrideQuery === 'string' ? overrideQuery : input).trim();
    if (!query || isLoading) return;
    setInput('');

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMsg);
    setIsLoading(true);

    try {
      const res: ChatResponse = await api.chat.send(currentUser.id, query, sessionId);
      setBackendDown(false);
      // If backend returns a DIFFERENT session ID (e.g. because previous was closed), reset chat
      if (res.session_id && sessionId && res.session_id !== sessionId) {
         setMessages([userMsg]);
         setSessionId(res.session_id);
         localStorage.setItem(activeSessionKey, res.session_id);
      } else if (res.session_id) {
         setSessionId(res.session_id);
         localStorage.setItem(activeSessionKey, res.session_id);
      }

      const isTroubleshooting = Array.isArray(res.steps) && res.steps.length > 0;
            const botMsg: ChatMessage & { meta?: MessageMeta } = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: res.response,
        timestamp: new Date().toISOString(),
        type: res.escalated ? 'escalation' : isTroubleshooting ? 'step' : 'answer',
        meta: {
          confidence_band: res.confidence_band,
          session_id: res.session_id,
          interaction_id: res.interaction_id,
          escalated: res.escalated,
          jira_reference: res.jira_reference,
          step_index: isTroubleshooting ? 0 : undefined,
          total_steps: isTroubleshooting ? res.steps!.length : undefined,
          ask_relevance: res.ask_relevance,
        },
      };
      addMessage(botMsg);
      // Refresh sessions to show the new title or status
      fetchSessions();

    } catch (error) {
      console.error('Chat send failed:', error);
      let healthReachable = false;
      try {
        await api.health();
        healthReachable = true;
        setBackendDown(false);
      } catch {
        setBackendDown(true);
      }
      addMessage({
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: healthReachable
          ? "I couldn't send that message, but the backend is reachable. Please try again, or check the browser console for the request error."
          : "I'm having trouble connecting to the backend. Please check the server is running or try again shortly.",
        timestamp: new Date().toISOString(),
        type: 'answer',
      });
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, currentUser.id, sessionId, activeSessionKey, addMessage]);

  const handleStepResponse = useCallback(async (msgId: string, meta: MessageMeta, resolved: boolean) => {
    if (!meta.session_id || !meta.interaction_id || meta.step_index == null) return;
    setResolvedMsgIds(prev => new Set(prev).add(msgId));
    setIsLoading(true);
    try {
      const res = await api.chat.stepResponse(
        meta.session_id,
        meta.interaction_id,
        meta.step_index,
        resolved
      );
      // Determine message type from StepResponseOut fields
      const isEscalated = res.escalated;
      const hasNextStep = res.next_step != null && res.step_index != null;
      const type = isEscalated ? 'escalation' : hasNextStep ? 'step' : 'answer';

      // Content: show the message; if there's a next step, append it
      const content = res.next_step
        ? `${res.message}\n\n**Step ${(res.step_index ?? 0) + 1}:** ${res.next_step}\n\nDid that resolve your issue?`
        : res.message;

      addMessage({
        id: `a-${Date.now()}`,
        role: 'assistant',
        content,
        timestamp: new Date().toISOString(),
        type,
        meta: {
          session_id: meta.session_id,
          interaction_id: meta.interaction_id,
          escalated: isEscalated,
          jira_reference: res.jira_reference,
          step_index: res.step_index ?? undefined,
          needs_rating: res.prompt_rating,
        },
      });
      fetchSessions();
    } catch {
      addMessage({
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      });
    } finally {
      setIsLoading(false);
    }
  }, [addMessage, fetchSessions]);

  const handleRate = useCallback(async (interactionId: string, rating: number) => {
    setRatedIds(prev => new Set(prev).add(interactionId));
    try {
      await api.chat.rate(interactionId, rating);
    } catch {
      // non-critical
    }
  }, []);

  const copySession = () => {
    if (sessionId) {
      navigator.clipboard.writeText(sessionId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const currentSession = sessions.find(s => s.id === sessionId);
  const isSessionClosed = currentSession && (currentSession.status === 'escalated' || currentSession.status === 'resolved');

  return (
    <div className="flex h-full w-full bg-white">
      {/* Sidebar */}
      <div className="w-64 border-r border-gray-100 bg-gray-50 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={loadNewChat}
            className="w-full flex items-center justify-center gap-2 bg-brand-700 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-brand-600 transition-colors shadow-sm"
          >
            <MessageSquarePlus size={16} /> New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map(s => (
            <button
              key={s.id}
              onClick={() => loadSessionHistory(s.id)}
              className={`w-full text-left p-3 rounded-lg text-sm transition-colors flex items-start gap-3 ${
                sessionId === s.id
                  ? 'bg-brand-50 text-brand-900 border border-brand-100'
                  : 'text-gray-700 hover:bg-gray-100 border border-transparent'
              }`}
            >
              <MessageSquare size={16} className={`mt-0.5 flex-shrink-0 ${sessionId === s.id ? 'text-brand-600' : 'text-gray-400'}`} />
              <div className="min-w-0">
                <div className="truncate font-medium">{s.title}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-gray-500">{new Date(s.created_at).toLocaleDateString()}</span>
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    s.status === 'escalated' ? 'bg-orange-100 text-orange-700' :
                    s.status === 'resolved' ? 'bg-green-100 text-green-700' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {s.status}
                  </span>
                </div>
              </div>
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="text-xs text-center text-gray-400 mt-10">No previous chats</p>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative">
      {/* Degradation banner */}
      {backendDown && (
        <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 flex items-center gap-2">
          <AlertCircle size={14} className="text-yellow-600" />
          <span className="text-xs text-yellow-700 font-medium">Running in limited mode — backend unreachable</span>
        </div>
      )}

      {/* Chat header */}
      <div className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-brand-700 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Leila</p>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-400 rounded-full" />
              <span className="text-xs text-gray-400">Online</span>
            </div>
          </div>
        </div>
        {sessionId && (
          <button
            onClick={copySession}
            className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors border border-gray-100"
            aria-label="Copy session ID"
          >
            {copied ? <CheckCheck size={13} className="text-green-500" /> : <Copy size={13} />}
            <span className="font-mono">{sessionId.slice(0, 8)}…</span>
          </button>
        )}
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto px-4 py-6 space-y-6 bg-gray-50"
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
      >
        {messages.map(msg => {
          const isUser = msg.role === 'user';
          const meta = msg.meta;
          const msgInteractionId = meta?.interaction_id;

          return (
            <div key={msg.id} className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
              {!isUser && (
                <div className="w-8 h-8 rounded-full bg-brand-700 flex items-center justify-center flex-shrink-0">
                  <Bot size={16} className="text-white" />
                </div>
              )}
              <div className={`flex flex-col max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
                {/* Step progress */}
                {!isUser && meta?.step_index != null && meta.total_steps != null && (
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <ChevronRight size={13} className="text-brand-500" />
                    <span className="text-xs font-medium text-brand-600">
                      Step {meta.step_index + 1} of {meta.total_steps}
                    </span>
                  </div>
                )}

                {/* Bubble */}
                <div
                  className={`px-4 py-3 rounded-2xl shadow-sm ${
                    isUser
                      ? 'bg-brand-700 text-white rounded-br-sm'
                      : 'bg-white border border-gray-100 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {isUser ? (
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  ) : (
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {msg.content.split(/(\*\*.*?\*\*)/g).map((part, i) => {
                        if (part.startsWith('**') && part.endsWith('**')) {
                          return (
                            <strong key={i} className="font-semibold text-gray-900">
                              {part.slice(2, -2)}
                            </strong>
                          );
                        }
                        return <span key={i}>{part}</span>;
                      })}
                    </div>
                  )}
                </div>

                {/* Timestamp */}
                <span className="text-[11px] text-gray-400 mt-1 px-1">
                  {format(new Date(msg.timestamp), 'HH:mm')}
                </span>

                {/* Escalation card */}
                {!isUser && meta?.escalated && (
                  <EscalationCard jiraRef={meta.jira_reference} />
                )}

                {/* Step action buttons */}
                {!isUser && msg.type === 'step' && !resolvedMsgIds.has(msg.id) && !isLoading && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleStepResponse(msg.id, meta!, true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors"
                    >
                      <CheckCircle2 size={13} /> Resolved
                    </button>
                    <button
                      onClick={() => handleStepResponse(msg.id, meta!, false)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Next Step →
                    </button>
                  </div>
                )}

                {/* Helpfulness buttons for LOW confidence */}
                {!isUser && meta?.ask_relevance && !meta.escalated && (
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-gray-500">Was this helpful?</span>
                    <button className="px-3 py-1 text-xs bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 transition-colors">
                      Yes
                    </button>
                    <button className="px-3 py-1 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg hover:bg-red-100 transition-colors">
                      No
                    </button>
                  </div>
                )}

                {/* Quick Reply Options */}
                {!isUser && meta?.options && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {meta.options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(opt)}
                        disabled={isLoading}
                        className="px-3 py-1.5 text-xs font-medium bg-white border border-brand-200 text-brand-700 rounded-full hover:bg-brand-50 transition-colors shadow-sm disabled:opacity-50 text-left"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                {/* Star rating */}
                {!isUser && meta?.needs_rating && msgInteractionId && !ratedIds.has(msgInteractionId) && (
                  <StarRating onRate={n => handleRate(msgInteractionId, n)} />
                )}
                {!isUser && meta?.needs_rating && msgInteractionId && ratedIds.has(msgInteractionId) && (
                  <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                    <CheckCircle2 size={12} /> Feedback recorded
                  </p>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="bg-white border-t border-gray-100 px-4 py-4">
        {isSessionClosed ? (
          <div className="text-center py-3 bg-gray-50 border border-gray-200 rounded-xl">
             <p className="text-sm text-gray-600 mb-2">This session has been {currentSession.status}.</p>
             <button onClick={loadNewChat} className="text-sm font-medium text-brand-600 hover:text-brand-700 underline">
               Start a New Chat
             </button>
          </div>
        ) : (
          <React.Fragment>
            <div className="flex items-end gap-3 bg-gray-50 rounded-2xl border border-gray-200 px-4 py-3 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100 transition-all">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Leila something..."
                rows={1}
                className="flex-1 bg-transparent resize-none text-sm text-gray-800 placeholder-gray-400 outline-none max-h-32"
                aria-label="Chat input"
                disabled={isLoading}
                style={{ minHeight: '24px' }}
                onInput={e => {
                  const el = e.currentTarget;
                  el.style.height = 'auto';
                  el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="w-9 h-9 rounded-xl bg-brand-700 flex items-center justify-center text-white hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                aria-label="Send message"
              >
                <Send size={16} />
              </button>
            </div>
            <p className="text-[11px] text-gray-400 mt-2 text-center">
              Leila may make mistakes. For urgent issues, contact IT directly.
            </p>
          </React.Fragment>
        )}
      </div>
      </div>
    </div>
  );
}
