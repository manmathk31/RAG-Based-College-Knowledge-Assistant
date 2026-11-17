import { useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Bot,
  GraduationCap,
  Menu,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  X,
  FileText,
  ExternalLink,
  User,
  LogIn,
  LogOut,
  Copy,
  Check,
  Trash2
} from "lucide-react";
import { fetchHealth, sendChatQuery } from "./services/api";
import type { ChatTurn, HealthStatus, SourceCitation } from "./types/api";
import type { Student } from "./services/auth";
import KnowledgeBase from "./components/KnowledgeBase";
import MarkdownRenderer from "./components/MarkdownRenderer";

interface AppProps {
  student: Student | null;
  isGuest: boolean;
  onOpenLogin: () => void;
  onSignOut: () => void;
}

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  mode?: string;
  time: string;
};

interface ConversationSession {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: string;
}

const suggestions = [
  "What is the minimum attendance requirement?",
  "Explain the exam revaluation process",
  "Where can I find scholarship information?",
  "What hostel facilities are available?"
];

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function App({ student, isGuest, onOpenLogin, onSignOut }: AppProps) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "knowledge">("chat");
  const [activeSources, setActiveSources] = useState<string | null>(null);
  const [highlightedCite, setHighlightedCite] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Active chat messages
  const [messages, setMessages] = useState<Message[]>([]);

  // Persistent recent conversation history stored in localStorage
  const [history, setHistory] = useState<ConversationSession[]>(() => {
    try {
      const saved = localStorage.getItem("mitaoe_chat_history");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const endRef = useRef<HTMLDivElement>(null);

  // Save history to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("mitaoe_chat_history", JSON.stringify(history));
    } catch {}
  }, [history]);

  // Periodic health check every 15 seconds
  useEffect(() => {
    let active = true;
    const check = () => {
      fetchHealth()
        .then((h) => {
          if (active) {
            setHealth(h);
            setHealthError(false);
          }
        })
        .catch(() => {
          if (active) {
            setHealth(null);
            setHealthError(true);
          }
        });
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (activeTab === "chat") {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, busy, activeTab]);

  const chatHistory = useMemo<ChatTurn[]>(
    () => messages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
    [messages]
  );

  const startNewChat = () => {
    if (messages.length > 0) {
      const firstUserMsg = messages.find((m) => m.role === "user")?.content || "Conversation";
      const title = firstUserMsg.slice(0, 42) + (firstUserMsg.length > 42 ? "…" : "");
      const session: ConversationSession = {
        id: makeId(),
        title,
        messages: [...messages],
        updatedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setHistory((prev) => [session, ...prev.filter((p) => p.id !== session.id)].slice(0, 15));
    }
    setMessages([]);
    setQuestion("");
    setActiveSources(null);
    setActiveTab("chat");
    setMobileOpen(false);
  };

  const restoreSession = (item: ConversationSession) => {
    // If current conversation has messages, save it first
    if (messages.length > 0 && !history.some((h) => h.messages === messages)) {
      const firstUserMsg = messages.find((m) => m.role === "user")?.content || "Previous conversation";
      const title = firstUserMsg.slice(0, 42) + (firstUserMsg.length > 42 ? "…" : "");
      setHistory((prev) => [
        {
          id: makeId(),
          title,
          messages: [...messages],
          updatedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
        ...prev,
      ].slice(0, 15));
    }
    setMessages(item.messages);
    setActiveTab("chat");
    setMobileOpen(false);
  };

  const deleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setHistory((prev) => prev.filter((h) => h.id !== id));
  };

  const ask = async (text: string) => {
    const clean = text.trim();
    if (!clean || busy) return;

    setActiveTab("chat");
    const next: Message = {
      id: makeId(),
      role: "user",
      content: clean,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const prior = chatHistory;
    setMessages((m) => [...m, next]);
    setQuestion("");
    setBusy(true);

    try {
      const result = await sendChatQuery({ message: clean, history: prior });
      setMessages((m) => [
        ...m,
        {
          id: makeId(),
          role: "assistant",
          content: result.answer,
          sources: result.sources || [],
          mode: result.retrieval_mode,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: makeId(),
          role: "assistant",
          content: `I could not connect to the college knowledge service: ${
            e instanceof Error ? e.message : "Request failed."
          }\n\nPlease verify that the backend is running at http://localhost:8000 and try asking again.`,
          sources: [],
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Student Initials
  const studentInitials = useMemo(() => {
    if (!student?.full_name) return "";
    return student.full_name
      .split(" ")
      .map((w) => w[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }, [student]);

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          className="mobile-scrim"
          onClick={() => setMobileOpen(false)}
          aria-label="Close menu"
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <GraduationCap size={24} />
          </div>
          <div>
            <b>MIT Academy of Engineering</b>
            <span>College Knowledge Assistant</span>
          </div>
          <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>

        <button className="new-chat" onClick={startNewChat}>
          <Plus size={17} /> New conversation
        </button>

        <div className="side-label">WORKSPACE</div>
        <button
          type="button"
          className={`side-link ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("chat");
            setMobileOpen(false);
          }}
        >
          <MessageSquare size={17} /> Ask the assistant
        </button>
        <button
          type="button"
          className={`side-link ${activeTab === "knowledge" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("knowledge");
            setMobileOpen(false);
          }}
        >
          <BookOpen size={17} /> Knowledge base
        </button>

        <div className="side-label history-label">RECENT CONVERSATIONS</div>
        <div className="history-list">
          {history.map((h) => (
            <div key={h.id} className="history-item-wrap">
              <button
                className="history-item"
                onClick={() => restoreSession(h)}
                title={h.title}
              >
                <MessageSquare size={14} />
                <span>{h.title}</span>
              </button>
              <button
                type="button"
                className="history-del-btn"
                onClick={(e) => deleteSession(e, h.id)}
                title="Delete this conversation"
                aria-label="Delete conversation"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {!history.length && (
            <p className="empty-history">Your recent conversations will appear here.</p>
          )}
        </div>

        <div className="sidebar-bottom">
          {/* User Account Bar in Sidebar */}
          <div className="sidebar-user-card">
            {student ? (
              <div className="side-user-info">
                <div className="side-user-avatar" title={student.full_name}>
                  {studentInitials || <GraduationCap size={16} />}
                </div>
                <div className="side-user-names">
                  <b>{student.full_name}</b>
                  <small>{student.email}</small>
                </div>
                <button
                  type="button"
                  className="side-logout-btn"
                  onClick={onSignOut}
                  title="Sign out of student account"
                >
                  <LogOut size={15} />
                </button>
              </div>
            ) : (
              <div className="side-user-info guest">
                <div className="side-user-avatar guest" title="Guest Visitor">
                  <User size={16} />
                </div>
                <div className="side-user-names">
                  <b>Guest Visitor</b>
                  <small>Public Information Access</small>
                </div>
                <button
                  type="button"
                  className="side-login-btn"
                  onClick={onOpenLogin}
                  title="Sign in with your student account"
                >
                  <LogIn size={15} /> Sign in
                </button>
              </div>
            )}
          </div>

          {/* Backend Connection Status */}
          <div className="connection">
            <span
              className={`status-dot ${health ? "online" : healthError ? "offline" : ""}`}
            />
            <div>
              <b>{health ? "Knowledge service online" : healthError ? "Backend offline" : "Checking connection"}</b>
              <small>{health ? `${health.project_name} · v${health.version}` : "http://localhost:8000"}</small>
            </div>
          </div>

          <div className="privacy-note">
            <ShieldCheck size={16} />
            <span>Answers are grounded in official MITAOE documents.</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-panel">
        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>

          <div>
            <div className="top-title">
              {activeTab === "chat" ? "College Knowledge Assistant" : "Knowledge Base Catalog"}
            </div>
            <div className="top-sub">
              <span
                className={`status-dot ${health ? "online" : healthError ? "offline" : ""}`}
              />
              {health
                ? "Connected to MITAOE Knowledge Engine"
                : healthError
                ? "Backend service unreachable (Ensure backend is running on port 8000)"
                : "Checking backend connectivity..."}
            </div>
          </div>

          <div className="top-right">
            <span className="secure-label">
              <ShieldCheck size={15} /> Official Institute Information
            </span>

            {/* User Profile in Topbar (NO confusing random 'S' symbol!) */}
            {student ? (
              <div className="top-user-pill">
                <div className="avatar student-avatar" title={student.full_name}>
                  {studentInitials || <GraduationCap size={16} />}
                </div>
                <div className="top-user-details">
                  <b>{student.full_name}</b>
                  <small>Student</small>
                </div>
                <button
                  type="button"
                  className="top-auth-btn sign-out"
                  onClick={onSignOut}
                  title="Sign out of student account"
                >
                  <LogOut size={14} />
                  <span>Sign out</span>
                </button>
              </div>
            ) : (
              <div className="top-user-pill guest">
                <div className="avatar guest-avatar" title="Guest Visitor">
                  <User size={16} />
                </div>
                <div className="top-user-details">
                  <b>Guest</b>
                  <small>Public</small>
                </div>
                <button
                  type="button"
                  className="top-auth-btn sign-in"
                  onClick={onOpenLogin}
                  title="Sign in with student account"
                >
                  <LogIn size={14} />
                  <span>Student Sign In</span>
                </button>
              </div>
            )}
          </div>
        </header>

        {activeTab === "knowledge" ? (
          <KnowledgeBase
            onSelectQuestion={(q) => {
              setActiveTab("chat");
              void ask(q);
            }}
          />
        ) : (
          <>
            <section className="chat-area">
              {messages.length === 0 ? (
                <div className="welcome-wrap">
                  <div className="welcome-icon">
                    <GraduationCap size={32} />
                  </div>
                  <div className="eyebrow">
                    <Sparkles size={14} /> MIT ACADEMY OF ENGINEERING
                  </div>
                  <h1>
                    How can we help<br />
                    <span>you today?</span>
                  </h1>
                  <p className="welcome-copy">
                    Ask about admissions, academic policies, attendance criteria, examinations,
                    fees, scholarships, placements, and campus hostel facilities.
                    {isGuest && " You are browsing in guest mode without needing an account."}
                  </p>

                  <div className="suggestion-grid">
                    {suggestions.map((s, i) => (
                      <button key={s} className="suggestion" onClick={() => ask(s)}>
                        <span className="suggestion-icon">
                          {[
                            <BookOpen size={17} key="1" />,
                            <FileText size={17} key="2" />,
                            <ShieldCheck size={17} key="3" />,
                            <GraduationCap size={17} key="4" />,
                          ][i]}
                        </span>
                        <span>{s}</span>
                        <ExternalLink size={14} className="suggestion-arrow" />
                      </button>
                    ))}
                  </div>

                  <div className="grounding-note">
                    <ShieldCheck size={16} />
                    <span>
                      Responses are strictly synthesized from official college documents. Always
                      verify critical deadlines with the respective departmental office.
                    </span>
                  </div>
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((m) => (
                    <article key={m.id} className={`message-row ${m.role}`}>
                      {/* Avatar for each message (Bot for assistant, User icon / initials for user) */}
                      <div className={`message-avatar ${m.role}`}>
                        {m.role === "assistant" ? (
                          <Bot size={19} />
                        ) : student ? (
                          <span>{studentInitials || "ST"}</span>
                        ) : (
                          <User size={17} />
                        )}
                      </div>

                      <div className="message-content">
                        <div className="message-meta">
                          {m.role === "assistant"
                            ? "College Knowledge Assistant"
                            : student
                            ? `${student.full_name} (Student)`
                            : "You (Guest)"}
                          <span>{m.time}</span>
                        </div>

                        <div className="message-bubble">
                          {m.role === "assistant" ? (
                            <MarkdownRenderer
                              content={m.content}
                              onCitationClick={(citeNum) => {
                                setActiveSources(m.id);
                                setHighlightedCite(citeNum);
                              }}
                            />
                          ) : (
                            m.content
                          )}

                          {m.role === "assistant" && (
                            <button
                              type="button"
                              className="copy-btn"
                              onClick={() => copyToClipboard(m.id, m.content)}
                              title="Copy answer to clipboard"
                            >
                              {copiedId === m.id ? (
                                <>
                                  <Check size={13} /> <span>Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={13} /> <span>Copy</span>
                                </>
                              )}
                            </button>
                          )}
                        </div>

                        {/* Citations and Sources block */}
                        {m.role === "assistant" && !!m.sources?.length && (
                          <div className="sources-block">
                            <button
                              type="button"
                              className="sources-heading"
                              onClick={() =>
                                setActiveSources(activeSources === m.id ? null : m.id)
                              }
                            >
                              <BookOpen size={15} /> Sources consulted ({m.sources.length})
                              <span>{activeSources === m.id ? "−" : "+"}</span>
                            </button>

                            {(activeSources === m.id ? m.sources : m.sources.slice(0, 2)).map(
                              (s, idx) => {
                                const citeNum = s.citation_id || String(idx + 1);
                                const isHighlighted =
                                  activeSources === m.id && highlightedCite === citeNum;

                                return (
                                  <div
                                    className={`source-card ${isHighlighted ? "highlighted" : ""}`}
                                    key={s.citation_id + s.chunk_id}
                                  >
                                    <div className="source-file">
                                      <span className="source-num-badge">[{citeNum}]</span>
                                      <FileText size={15} />
                                      <b>{s.document_name}</b>
                                      <span>Page {s.page_number ?? "—"}</span>
                                    </div>
                                    {s.section && <small className="source-sec">{s.section}</small>}
                                    <p>{s.snippet}</p>
                                  </div>
                                );
                              }
                            )}
                          </div>
                        )}

                        {m.role === "assistant" && m.mode && (
                          <div className="retrieval-tag">
                            Strategy: {m.mode.replace("_", " ")}
                          </div>
                        )}
                      </div>
                    </article>
                  ))}

                  {busy && (
                    <article className="message-row assistant">
                      <div className="message-avatar assistant">
                        <Bot size={19} />
                      </div>
                      <div className="message-content">
                        <div className="message-meta">College Knowledge Assistant</div>
                        <div className="typing">
                          <i />
                          <i />
                          <i /> Searching official college documents and preparing answer...
                        </div>
                      </div>
                    </article>
                  )}
                  <div ref={endRef} />
                </div>
              )}
            </section>

            {/* Input Composer */}
            <footer className="composer-wrap">
              <form
                className="composer"
                onSubmit={(e) => {
                  e.preventDefault();
                  void ask(question);
                }}
              >
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void ask(question);
                    }
                  }}
                  placeholder="Ask about admissions, attendance policy, exams, fees, scholarships, or hostels..."
                  rows={1}
                  maxLength={2000}
                />
                <button
                  type="submit"
                  disabled={!question.trim() || busy}
                  aria-label="Send question"
                  title="Send question"
                >
                  <Send size={18} />
                </button>
              </form>

              <div className="composer-foot">
                <span>Press Enter to send · Shift + Enter for new line</span>
                <span>{question.length}/2000</span>
              </div>

              <div className="disclaimer">
                Grounded in official MITAOE documents. For authoritative decision notices, refer to
                the cited official college handbook.
              </div>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
