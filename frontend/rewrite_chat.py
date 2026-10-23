import re

with open("frontend/src/components/chat/ChatInterface.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add MessageSquarePlus and MessageSquare to lucide-react imports
content = re.sub(
    r"CheckCircle2,\n} from 'lucide-react';",
    "CheckCircle2,\n  MessageSquarePlus,\n  MessageSquare,\n} from 'lucide-react';",
    content
)

# 2. Add SessionData interface
session_iface = """
interface SessionData {
  id: string;
  title: string;
  status: string;
  created_at: string;
}
"""
content = content.replace("function TypingIndicator() {", session_iface + "\nfunction TypingIndicator() {")

# 3. Modify ChatInterface component to include session state and functions
chat_iface_start = """export function ChatInterface() {
  const { currentUser } = useRole();
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
    setSessionId(undefined);
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: `Hi ${currentUser.name.split(' ')[0]}! I'm Leila, your IT Help Desk assistant. I can help you with:\\n\\n• Wi-Fi and network issues\\n• Software installation and configuration\\n• Access requests and provisioning\\n• Hardware troubleshooting\\n• Account and password issues\\n\\nWhat can I help you with today?`,
        timestamp: new Date().toISOString(),
        type: 'answer',
      },
    ]);
  }, [currentUser.name]);

  const loadSessionHistory = useCallback(async (sid: string) => {
    setSessionId(sid);
    setIsLoading(true);
    try {
      const data = await api.chat.getSessionHistory(sid);
      if (data && data.messages) {
        setMessages(data.messages as any);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize with new chat on first load
  useEffect(() => {
    loadNewChat();
  }, [loadNewChat]);
"""

# Replace the start of ChatInterface up to the handleSend
content = re.sub(r"export function ChatInterface\(\) \{.*?(?=  useEffect\(\(\) => \{\n    bottomRef\.current\?\.scrollIntoView)", chat_iface_start, content, flags=re.DOTALL)


# 4. Modify handleSend to refresh sessions list after sending a message
handle_send_end = """      const botMsg: ChatMessage & { meta?: MessageMeta } = {
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
"""
content = re.sub(r"const botMsg: ChatMessage.*?addMessage\(botMsg\);", handle_send_end, content, flags=re.DOTALL)


# 5. Modify stepResponse to also refresh sessions if escalated/resolved
step_resp_end = """        },
      });
      fetchSessions();
    } catch {"""
content = re.sub(r"        },\n      \}\);\n    \} catch \{", step_resp_end, content)


# 6. Change the main return layout to include the sidebar
old_return = """  return (
    <div className="flex flex-col h-full">
      {/* Degradation banner */}"""

new_return = """  return (
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
      {/* Degradation banner */}"""

content = content.replace(old_return, new_return)

with open("frontend/src/components/chat/ChatInterface.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated ChatInterface.tsx successfully")
