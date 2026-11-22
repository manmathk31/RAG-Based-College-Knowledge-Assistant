import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  ChevronDown,
  Clock,
  Copy,
  FileText,
  Globe,
  HelpCircle,
  History,
  MessageSquare,
  Moon,
  Plus,
  RotateCcw,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import { fetchHealth, sendChatQuery } from "./services/api";
import type { ChatTurn, HealthStatus, SourceCitation, ExtractedEntity, SentimentData } from "./types/api";
import { Logo } from "./components/Logo";
import MarkdownRenderer from "./components/MarkdownRenderer";
import { FaqView } from "./components/FaqView";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  mode?: string;
  timestamp: string;
  language?: string;
  topics?: string[];
  entities?: ExtractedEntity[];
  sentiment?: SentimentData;
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
  const [activeTab, setActiveTab] = useState<"chat" | "faq">("chat");
  const [selectedLang, setSelectedLang] = useState<"auto" | "en" | "mr" | "hi">("auto");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

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
        language: selectedLang === "auto" ? undefined : selectedLang,
      });

      const assistantMsg: Message = {
        id: makeId(),
        role: "assistant",
        content: response.answer,
        sources: response.sources || [],
        mode: response.retrieval_mode,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        language: response.language,
        topics: response.topics,
        entities: response.entities,
        sentiment: response.sentiment,
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

  const handleCitationNumClick = (numStr: string, sources?: SourceCitation[], msgId?: string) => {
    if (!sources || sources.length === 0) return;
    if (msgId) {
      setExpandedSources((prev) => ({ ...prev, [msgId]: true }));
    }
    const idx = parseInt(numStr, 10) - 1;
    if (sources[idx]) {
      setSelectedCitation(sources[idx]);
    } else if (sources[0]) {
      setSelectedCitation(sources[0]);
    }
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

        {/* Navigation Switcher */}
        <nav className="tab-switcher" aria-label="Main Navigation">
          <button
            className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <MessageSquare size={13} />
            <span>Chat</span>
          </button>
          <button
            className={`tab-btn ${activeTab === "faq" ? "active" : ""}`}
            onClick={() => setActiveTab("faq")}
          >
            <HelpCircle size={13} />
            <span className="tab-label-full">Most Asked</span>
            <span className="tab-label-short">FAQs</span>
          </button>
        </nav>

        <div className="topbar-right">
          <button
            className="icon-btn"
            onClick={() => setIsDark((prev) => !prev)}
            aria-label="Toggle theme"
            title={isDark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDark ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          <button className="new-chat-btn" onClick={handleNewChat} title="Start new conversation">
            <Plus size={15} />
            <span className="new-chat-text">New chat</span>
          </button>
        </div>
      </header>

      {/* Tab Views */}
      {activeTab === "chat" ? (
        <>
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

                  {/* Most Asked Quick Launch Banner */}
                  <button
                    className="catalog-launch-banner"
                    onClick={() => setActiveTab("faq")}
                  >
                    <div className="catalog-launch-icon">
                      <BookOpen size={15} />
                    </div>
                    <div className="catalog-launch-content">
                      <span className="catalog-launch-title">Browse all 6 Official College Handbooks & FAQs</span>
                      <span className="catalog-launch-sub">Attendance rules, ATKT, fees, hostels & scholarship guidelines</span>
                    </div>
                    <ArrowRight size={14} className="catalog-launch-arrow" />
                  </button>
                </div>
              ) : (
                /* Active Messages */
                messages.map((m) => (
                  <div key={m.id} className={`message-item ${m.role}`}>
                    {m.role === "user" ? (
                      <div className="user-bubble">{m.content}</div>
                    ) : (
                      <div className="assistant-body">
                        <MarkdownRenderer
                          content={m.content}
                          onCitationClick={(num) => handleCitationNumClick(num, m.sources, m.id)}
                        />

                        {/* Live Extracted Institutional Entities & Topics (CO2 Demonstration) */}
                        {((m.topics && m.topics.length > 0) || (m.entities && m.entities.length > 0) || m.sentiment) && (
                          <div className="nlp-insights-bar">
                            <div className="nlp-header-row">
                              <span className="nlp-insights-tag">
                                <Sparkles size={11} className="nlp-sparkle-icon" />
                                <span>NLP Topics & Entities</span>
                              </span>
                              {m.language && m.language !== "en" && (
                                <span className="nlp-lang-badge">
                                  {m.language === "mr" ? "मराठी (Marathi)" : "हिंदी (Hindi)"}
                                </span>
                              )}
                            </div>

                            {/* Sentiment Banner if present */}
                            {m.sentiment && (
                              <div className={`nlp-sentiment-badge sentiment-${m.sentiment.overall_sentiment}`}>
                                <span className="sentiment-dot" />
                                <span className="sentiment-label">
                                  Review Sentiment: <strong>{m.sentiment.overall_sentiment.toUpperCase()}</strong> ({m.sentiment.polarity_score > 0 ? `+${m.sentiment.polarity_score}` : m.sentiment.polarity_score})
                                </span>
                                {m.sentiment.aspects && m.sentiment.aspects.length > 0 && (
                                  <span className="sentiment-aspects">
                                    · {m.sentiment.aspects.map((a) => `${a.aspect}: ${a.sentiment}`).join(", ")}
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Entities Chips */}
                            {m.entities && m.entities.length > 0 && (
                              <div className="nlp-entities-chips">
                                {m.entities.map((ent, idx) => (
                                  <span
                                    key={idx}
                                    className={`nlp-entity-chip cat-${ent.category.toLowerCase().replace(/_/g, "-")}`}
                                    title={`Category: ${ent.category}`}
                                  >
                                    <span className="entity-cat-badge">{ent.category.replace(/_/g, " ")}</span>
                                    <span className="entity-text">{ent.text}</span>
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* High-level Topics */}
                            {m.topics && m.topics.length > 0 && (
                              <div className="nlp-topics-chips">
                                {m.topics.map((top, idx) => (
                                  <span key={idx} className="nlp-topic-pill">
                                    #{top}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Minimized & Expandable Source Citations */}
                        {m.sources && m.sources.length > 0 && (
                          <div className="sources-container">
                            <button
                              className={`sources-toggle-btn ${expandedSources[m.id] ? "expanded" : ""}`}
                              onClick={() => toggleSources(m.id)}
                              title={expandedSources[m.id] ? "Collapse sources" : "Expand sources consulted"}
                            >
                              <BookOpen size={11} className="source-toggle-icon" />
                              <span className="source-toggle-label">
                                {m.sources.length} {m.sources.length === 1 ? "source" : "sources"} consulted
                              </span>
                              <ChevronDown
                                size={12}
                                className={`source-toggle-chevron ${expandedSources[m.id] ? "rotated" : ""}`}
                              />
                            </button>

                            {expandedSources[m.id] && (
                              <div className="sources-row animated-expand">
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
              <div className="composer-lang-bar">
                <span className="composer-lang-label">
                  <Globe size={11} />
                  <span>Language:</span>
                </span>
                <div className="composer-lang-options">
                  <button
                    type="button"
                    className={`lang-pill ${selectedLang === "auto" ? "active" : ""}`}
                    onClick={() => setSelectedLang("auto")}
                    title="Auto-detect from input language"
                  >
                    Auto
                  </button>
                  <button
                    type="button"
                    className={`lang-pill ${selectedLang === "en" ? "active" : ""}`}
                    onClick={() => setSelectedLang("en")}
                    title="English"
                  >
                    English
                  </button>
                  <button
                    type="button"
                    className={`lang-pill ${selectedLang === "mr" ? "active" : ""}`}
                    onClick={() => setSelectedLang("mr")}
                    title="मराठी (Marathi)"
                  >
                    मराठी
                  </button>
                  <button
                    type="button"
                    className={`lang-pill ${selectedLang === "hi" ? "active" : ""}`}
                    onClick={() => setSelectedLang("hi")}
                    title="हिंदी (Hindi)"
                  >
                    हिंदी
                  </button>
                </div>
              </div>

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
        </>
      ) : (
        <FaqView
          onAskQuestion={(q) => {
            setActiveTab("chat");
            void handleSubmit(q);
          }}
        />
      )}

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

            <div className="drawer-catalog-box">
              <button
                className="drawer-handbook-btn"
                onClick={() => {
                  setDrawerOpen(false);
                  setActiveTab("faq");
                }}
              >
                <HelpCircle size={15} />
                <span>Most Asked FAQs & Handbooks</span>
              </button>
            </div>
          </aside>
        </>
      )}
    </div>
  );
}
