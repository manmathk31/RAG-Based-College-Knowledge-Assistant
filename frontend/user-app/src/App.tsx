import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUp,
  Check,
  Clock,
  Copy,
  FileText,
  History,
  Moon,
  Plus,
  RotateCcw,
  Sun,
  X,
} from "lucide-react";
import { fetchHealth, sendChatQuery } from "./services/api";
import type { ChatTurn, HealthStatus, SourceCitation } from "./types/api";
import { Logo } from "./components/Logo";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  mode?: string;
  timestamp: string;
}

interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  messages: Message[];
}

const STARTER_CARDS = [
  {
    title: "Attendance Criteria",
    desc: "Minimum percentage, medical leave & rules",
    query: "What is the minimum attendance requirement?",
  },
  {
    title: "Exam Revaluation",
    desc: "Verification process, timelines & application fees",
    query: "Explain the exam revaluation process",
  },
  {
    title: "Scholarship Information",
    desc: "Government schemes, eligibility & deadlines",
    query: "Where can I find scholarship information?",
  },
  {
    title: "Campus & Hostel",
    desc: "Room allocation, mess facilities & timings",
    query: "What hostel facilities are available?",
  },
];

const STORAGE_KEY = "college_assistant_saved_chats";
const THEME_KEY = "college_assistant_theme";

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Theme Management: Defaults strictly to Light Mode
  const [isDark, setIsDark] = useState<boolean>(() => {
    try {
      const savedTheme = localStorage.getItem(THEME_KEY);
      return savedTheme === "dark";
    } catch {
      return false;
    }
  });

  const [savedChats, setSavedChats] = useState<ChatSession[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync theme to HTML class
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem(THEME_KEY, "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem(THEME_KEY, "light");
    }
  }, [isDark]);

  // Initial health check
  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  // Save conversations
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(savedChats));
    } catch {
      // Ignore storage error
    }
  }, [savedChats]);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  // Auto-resize composer textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 130)}px`;
    }
  }, [input]);

  const priorTurns = useMemo<ChatTurn[]>(() => {
    return messages.slice(-10).map((m) => ({ role: m.role, content: m.content }));
  }, [messages]);

  const archiveCurrentChat = () => {
    if (messages.length > 0) {
      const firstUserMsg = messages.find((m) => m.role === "user")?.content || "Conversation";
      const title = firstUserMsg.length > 40 ? `${firstUserMsg.slice(0, 40)}…` : firstUserMsg;
      const newSession: ChatSession = {
        id: makeId(),
        title,
        timestamp: new Date().toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        messages,
      };
      setSavedChats((prev) => [newSession, ...prev.filter((c) => c.title !== title)].slice(0, 15));
    }
  };

  const handleNewChat = () => {
    archiveCurrentChat();
    setMessages([]);
    setInput("");
    setDrawerOpen(false);
  };

  const restoreChat = (session: ChatSession) => {
    archiveCurrentChat();
    setMessages(session.messages);
    setDrawerOpen(false);
  };

  const clearHistory = () => {
    setSavedChats([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRetryLast = () => {
    const lastUserQuery = [...messages].reverse().find((m) => m.role === "user")?.content;
    if (lastUserQuery) {
      void handleSubmit(lastUserQuery);
    }
  };

  const handleSubmit = async (queryText?: string) => {
    const textToSend = (queryText || input).trim();
    if (!textToSend || isSubmitting) return;

    const userMsg: Message = {
      id: makeId(),
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const historyPayload = priorTurns;
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsSubmitting(true);

    try {
      const response = await sendChatQuery({
        message: textToSend,
        history: historyPayload,
      });

      const assistantMsg: Message = {
        id: makeId(),
        role: "assistant",
        content: response.answer,
        sources: response.sources || [],
        mode: response.retrieval_mode,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: makeId(),
        role: "assistant",
        content:
          err instanceof Error
            ? `Unable to retrieve an answer: ${err.message}`
            : "An unexpected error occurred while communicating with the college knowledge base.",
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Structured prose rendering for assistant answers
  const renderFormattedProse = (text: string) => {
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      if (!line.trim()) {
        return <div key={idx} style={{ height: "6px" }} />;
      }

      // Bullet List
      if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
        return (
          <li key={idx} style={{ marginLeft: "18px", listStyleType: "disc", marginBottom: "4px" }}>
            {formatBold(line.trim().slice(2))}
          </li>
        );
      }

      // Numbered List
      const numberedMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
      if (numberedMatch) {
        return (
          <div key={idx} style={{ display: "flex", gap: "8px", marginBottom: "4px", paddingLeft: "4px" }}>
            <span style={{ fontWeight: 600, color: "var(--accent)" }}>{numberedMatch[1]}.</span>
            <span>{formatBold(numberedMatch[2])}</span>
          </div>
        );
      }

      return (
        <p key={idx} style={{ marginBottom: "8px" }}>
          {formatBold(line)}
        </p>
      );
    });
  };

  const formatBold = (str: string) => {
    const parts = str.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="app-viewport">
      {/* Minimal Topbar */}
      <header className="app-topbar">
        <div className="topbar-left">
          <button
            className="icon-btn"
            onClick={() => setDrawerOpen(true)}
            aria-label="Recent chats"
            title="Chat history"
          >
            <History size={18} />
          </button>

          <button
            onClick={handleNewChat}
            style={{ background: "transparent", border: "none", cursor: "pointer", display: "flex", alignItems: "center" }}
            title="College Knowledge Assistant"
          >
            <Logo size={32} animated={false} />
          </button>

          <span
            className="status-dot"
            title={health ? `Knowledge base ready · ${health.environment}` : "Checking backend status…"}
          />
        </div>

        <div className="topbar-right">
          <button
            className="icon-btn"
            onClick={() => setIsDark((prev) => !prev)}
            aria-label="Toggle theme"
            title={isDark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDark ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          <button className="new-chat-btn" onClick={handleNewChat}>
            <Plus size={14} />
            <span>New chat</span>
          </button>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="chat-scroll-area">
        <div className="chat-container">
          {messages.length === 0 ? (
            /* Welcome Hero */
            <div className="welcome-hero">
              <div className="welcome-logo-box">
                <Logo size={74} animated={true} />
              </div>

              <h1 className="welcome-title">What would you like to know?</h1>
              <p className="welcome-subtitle">
                Grounded answers with source citations from verified college documents.
              </p>

              {/* 4 Starter Cards */}
              <div className="starter-grid">
                {STARTER_CARDS.map((card) => (
                  <button
                    key={card.title}
                    className="starter-card"
                    onClick={() => handleSubmit(card.query)}
                  >
                    <div className="starter-card-header">
                      <span className="starter-card-title">{card.title}</span>
                      <ArrowUp size={14} className="starter-card-arrow" style={{ transform: "rotate(45deg)" }} />
                    </div>
                    <span className="starter-card-desc">{card.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Active Messages */
            messages.map((m) => (
              <div key={m.id} className={`message-item ${m.role}`}>
                {m.role === "user" ? (
                  <div className="user-bubble">{m.content}</div>
                ) : (
                  <div className="assistant-body">
                    <div className="assistant-prose">
                      {renderFormattedProse(m.content)}
                    </div>

                    {/* Source Citations Badges */}
                    {m.sources && m.sources.length > 0 && (
                      <div className="sources-row">
                        {m.sources.map((src, i) => (
                          <button
                            key={src.citation_id || `${src.chunk_id}-${i}`}
                            className="source-badge"
                            onClick={() => setSelectedCitation(src)}
                            title="View cited document passage"
                          >
                            <FileText size={12} />
                            <span className="source-badge-title">{src.document_name}</span>
                            {src.page_number !== null && (
                              <span className="source-badge-page">p.{src.page_number}</span>
                            )}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Action Bar */}
                    <div className="assistant-toolbar">
                      <button
                        className={`tool-btn ${copiedId === m.id ? "copied" : ""}`}
                        onClick={() => handleCopy(m.id, m.content)}
                        title="Copy answer to clipboard"
                      >
                        {copiedId === m.id ? (
                          <>
                            <Check size={12} />
                            <span>Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={12} />
                            <span>Copy</span>
                          </>
                        )}
                      </button>

                      <button
                        className="tool-btn"
                        onClick={handleRetryLast}
                        title="Regenerate answer"
                      >
                        <RotateCcw size={12} />
                        <span>Retry</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {/* Gentle 3-Dot Typing Pulse */}
          {isSubmitting && (
            <div className="message-item assistant">
              <div className="typing-dots">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </main>

      {/* Floating Bottom Composer */}
      <footer className="composer-dock">
        <div className="composer-inner">
          <form
            className="composer-card"
            onSubmit={(e) => {
              e.preventDefault();
              void handleSubmit();
            }}
          >
            <textarea
              ref={textareaRef}
              className="composer-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSubmit();
                }
              }}
              placeholder="Ask anything about college…"
              rows={1}
              maxLength={2000}
            />

            <button
              type="submit"
              className="send-btn"
              disabled={!input.trim() || isSubmitting}
              aria-label="Send query"
              title="Send (Enter)"
            >
              <ArrowUp size={16} strokeWidth={2.4} />
            </button>
          </form>
        </div>
      </footer>

      {/* Citation Details Sheet Modal */}
      {selectedCitation && (
        <div className="modal-backdrop" onClick={() => setSelectedCitation(null)}>
          <div className="citation-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 className="modal-doc-title">{selectedCitation.document_name}</h3>
                <span className="modal-badge">
                  {selectedCitation.page_number !== null
                    ? `Page ${selectedCitation.page_number}`
                    : "Official Document"}
                  {selectedCitation.section ? ` · ${selectedCitation.section}` : ""}
                </span>
              </div>
              <button
                className="icon-btn"
                onClick={() => setSelectedCitation(null)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-snippet-box">
              {selectedCitation.snippet}
            </div>
          </div>
        </div>
      )}

      {/* Slide-Out History Drawer */}
      {drawerOpen && (
        <>
          <div className="drawer-overlay" onClick={() => setDrawerOpen(false)} />
          <aside className="history-panel">
            <div className="history-header">
              <span className="history-title">Recent Chats</span>
              <button className="icon-btn" onClick={() => setDrawerOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="history-items">
              {savedChats.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: "13px", padding: "10px 4px" }}>
                  No previous conversations yet.
                </p>
              ) : (
                savedChats.map((chat) => (
                  <button
                    key={chat.id}
                    className="history-btn"
                    onClick={() => restoreChat(chat)}
                  >
                    <Clock size={14} style={{ color: "var(--accent)", flexShrink: 0 }} />
                    <span>{chat.title}</span>
                  </button>
                ))
              )}
            </div>

            {savedChats.length > 0 && (
              <div className="history-footer">
                <button className="clear-btn" onClick={clearHistory}>
                  Clear all history
                </button>
              </div>
            )}
          </aside>
        </>
      )}
    </div>
  );
}
