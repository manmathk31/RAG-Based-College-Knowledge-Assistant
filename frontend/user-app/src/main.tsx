import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Login from "./components/Login";
import { loginStudent, logoutStudent, restoreSession, setAccessToken, type Student } from "./services/auth";
import "./index.css";

function Root() {
  const [student, setStudent] = useState<Student | null>(null);
  const [showLogin, setShowLogin] = useState(false);
  const [checking, setChecking] = useState(true);
  useEffect(() => { let active = true; restoreSession().then((s) => { if (active) setStudent(s); }).finally(() => { if (active) setChecking(false); }); return () => { active = false; }; }, []);
  const signIn = async (email: string, password: string) => {
    const s = await loginStudent(email, password); setStudent(s); setShowLogin(false);
  };
  const signOut = async () => { try { await logoutStudent(); } finally { setAccessToken(null); setStudent(null); } };
  return <><div className="access-strip">
    <span>{checking ? "Checking session…" : student ? `Signed in: ${student.full_name}` : "Guest access · No account needed to explore college information"}</span>
    {student ? <button onClick={() => void signOut()}>Sign out</button> : <button onClick={() => setShowLogin(true)}>Student Login</button>}
  </div><App />
  {showLogin && <div className="login-overlay"><button className="login-close" onClick={() => setShowLogin(false)}>Continue as guest ✕</button><Login onLogin={signIn}/></div>}
  </>;
}
ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><Root /></React.StrictMode>);
