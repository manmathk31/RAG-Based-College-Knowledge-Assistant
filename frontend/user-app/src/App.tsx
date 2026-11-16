import { useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, Bot, GraduationCap, Menu, MessageSquare, Plus, Send, ShieldCheck, Sparkles, X, FileText, ExternalLink } from "lucide-react";
import { fetchHealth, sendChatQuery } from "./services/api";
import type { ChatTurn, HealthStatus, SourceCitation } from "./types/api";

type Message = { id: string; role: "user" | "assistant"; content: string; sources?: SourceCitation[]; mode?: string; time: string };
const suggestions = ["What is the minimum attendance requirement?", "Explain the exam revaluation process", "Where can I find scholarship information?", "What hostel facilities are available?"];
const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
function App() {
  const [health,setHealth] = useState<HealthStatus|null>(null);
  const [healthError,setHealthError] = useState(false);
  const [question,setQuestion] = useState("");
  const [busy,setBusy] = useState(false);
  const [mobileOpen,setMobileOpen] = useState(false);
  const [activeSources,setActiveSources] = useState<string|null>(null);
  const [messages,setMessages] = useState<Message[]>([]);
  const [history,setHistory] = useState<{id:string;title:string;messages:Message[]}[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(()=>{ fetchHealth().then(setHealth).catch(()=>setHealthError(true)); },[]);
  useEffect(()=>{ endRef.current?.scrollIntoView({behavior:"smooth"}); },[messages,busy]);
  const chatHistory = useMemo<ChatTurn[]>(()=>messages.slice(-10).map(m=>({role:m.role,content:m.content})),[messages]);
  const newChat = () => { if(messages.length) setHistory(h=>[{id:makeId(),title:messages.find(m=>m.role==="user")?.content.slice(0,42)||"New conversation",messages},...h].slice(0,12)); setMessages([]); setQuestion(""); setMobileOpen(false); };
  const ask = async (text:string) => {
    const clean=text.trim(); if(!clean || busy) return;
    const next:Message={id:makeId(),role:"user",content:clean,time:new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})};
    const prior=chatHistory;
    setMessages(m=>[...m,next]); setQuestion(""); setBusy(true);
    try {
      const result=await sendChatQuery({message:clean,history:prior});
      setMessages(m=>[...m,{id:makeId(),role:"assistant",content:result.answer,sources:result.sources||[],mode:result.retrieval_mode,time:new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}]);
    } catch(e) {
      setMessages(m=>[...m,{id:makeId(),role:"assistant",content:`I couldn't connect to the college knowledge service. ${e instanceof Error?e.message:"Please try again."} Check that the backend is running and try again.`,sources:[],time:new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}]);
    } finally { setBusy(false); }
  };
  const restore=(item:{id:string;title:string;messages:Message[]})=>{setMessages(item.messages);setMobileOpen(false);};
  return <div className="app-shell">
    {mobileOpen&&<button className="mobile-scrim" onClick={()=>setMobileOpen(false)} aria-label="Close menu"/>}
    <aside className={`sidebar ${mobileOpen?"sidebar-open":""}`}>
      <div className="brand"><div className="brand-mark"><GraduationCap size={24}/></div><div><b>MIT Academy of Engineering</b><span>College Knowledge Assistant</span></div><button className="mobile-close" onClick={()=>setMobileOpen(false)}><X size={18}/></button></div>
      <button className="new-chat" onClick={newChat}><Plus size={17}/> New conversation</button>
      <div className="side-label">WORKSPACE</div>
      <div className="side-link active"><MessageSquare size={17}/> Ask the assistant</div>
      <div className="side-link"><BookOpen size={17}/> Knowledge base</div>
      <div className="side-label history-label">RECENT CONVERSATIONS</div>
      <div className="history-list">{history.map(h=><button key={h.id} className="history-item" onClick={()=>restore(h)}><MessageSquare size={14}/><span>{h.title}</span></button>)}{!history.length&&<p className="empty-history">Your recent conversations will appear here.</p>}</div>
      <div className="sidebar-bottom"><div className="connection"><span className={`status-dot ${health?"online":""}`}/><div><b>{health?"Knowledge service online":"Service connection"}</b><small>{health?health.environment:"Checking backend status"}</small></div></div><div className="privacy-note"><ShieldCheck size={16}/><span>Answers are grounded in official college documents.</span></div></div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><button className="menu-button" onClick={()=>setMobileOpen(true)}><Menu size={20}/></button><div><div className="top-title">College Knowledge Assistant</div><div className="top-sub"><span className={`status-dot ${health?"online":""}`}/>{health?"Connected to college knowledge base":healthError?"Backend unavailable":"Checking connection"}</div></div><div className="top-right"><span className="secure-label"><ShieldCheck size={15}/> Official information assistant</span><div className="avatar">S</div></div></header>
      <section className="chat-area">
        {messages.length===0?<div className="welcome-wrap"><div className="welcome-icon"><GraduationCap size={31}/></div><div className="eyebrow"><Sparkles size={14}/> MITAOE COLLEGE INFORMATION</div><h1>How can we help<br/><span>you today?</span></h1><p className="welcome-copy">Ask about admissions, courses, eligibility, fees, placements, academics, examinations and campus facilities. Visitors and prospective students can chat without signing in.</p><div className="suggestion-grid">{suggestions.map((s,i)=><button key={s} className="suggestion" onClick={()=>ask(s)}><span className="suggestion-icon">{[<BookOpen size={17}/>,<FileText size={17}/>,<ShieldCheck size={17}/>,<GraduationCap size={17}/>][i]}</span><span>{s}</span><ExternalLink size={14} className="suggestion-arrow"/></button>)}</div><div className="grounding-note"><ShieldCheck size={16}/><span>Responses are generated from available college documents. Always verify critical deadlines with the relevant office.</span></div></div>
        :<div className="message-list">{messages.map(m=><article key={m.id} className={`message-row ${m.role}`}><div className={`message-avatar ${m.role}`}>{m.role==="assistant"?<Bot size={19}/>:<span>S</span>}</div><div className="message-content"><div className="message-meta">{m.role==="assistant"?"College Knowledge Assistant":"You"} <span>{m.time}</span></div><div className="message-bubble">{m.content}</div>{m.role==="assistant"&&!!m.sources?.length&&<div className="sources-block"><button className="sources-heading" onClick={()=>setActiveSources(activeSources===m.id?null:m.id)}><BookOpen size={15}/> Sources consulted ({m.sources.length}) <span>{activeSources===m.id?"−":"+"}</span></button>{(activeSources===m.id?m.sources:m.sources.slice(0,2)).map(s=><div className="source-card" key={s.citation_id+s.chunk_id}><div className="source-file"><FileText size={16}/><b>{s.document_name}</b><span>Page {s.page_number??"—"}</span></div>{s.section&&<small>{s.section}</small>}<p>{s.snippet}</p></div>)}</div>}{m.role==="assistant"&&m.mode&&<div className="retrieval-tag">Retrieval: {m.mode.replace("_"," ")}</div>}</div></article>)}{busy&&<article className="message-row assistant"><div className="message-avatar assistant"><Bot size={19}/></div><div className="message-content"><div className="message-meta">College Knowledge Assistant</div><div className="typing"><i/><i/><i/> Searching college documents and preparing an answer…</div></div></article>}<div ref={endRef}/></div>}
      </section>
      <footer className="composer-wrap"><form className="composer" onSubmit={e=>{e.preventDefault();void ask(question);}}><textarea value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();void ask(question);}}} placeholder="Ask about admissions, courses, fees, academics or campus facilities…" rows={1} maxLength={2000}/><button disabled={!question.trim()||busy} aria-label="Send question"><Send size={18}/></button></form><div className="composer-foot"><span>Press Enter to send · Shift + Enter for a new line</span><span>{question.length}/2000</span></div><div className="disclaimer">AI-generated responses may require verification. Refer to the cited official document for authoritative information.</div></footer>
    </main>
  </div>;
}
export default App;
