import { useState, type FormEvent } from "react";
import { GraduationCap, Mail, LockKeyhole, Eye, EyeOff, ArrowRight, ShieldCheck, UserCheck, Sparkles } from "lucide-react";
import "./Login.css";

interface LoginProps {
  onLogin: (email: string, password: string) => Promise<void>;
  onContinueGuest: () => void;
  isOverlay?: boolean;
}

export default function Login({ onLogin, onContinueGuest, isOverlay }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setBusy(true);
    setError("");
    try {
      await onLogin(email.trim().toLowerCase(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed. Please check your credentials.");
    } finally {
      setBusy(false);
    }
  };

  const fillDemo = () => {
    setEmail("student@mitaoe.ac.in");
    setPassword("Password123");
  };

  return (
    <main className={`auth-page ${isOverlay ? "auth-overlay-mode" : ""}`}>
      <section className="auth-left">
        <div className="auth-brand">
          <div className="auth-logo">
            <GraduationCap size={28} />
          </div>
          <div>
            <b>MIT Academy of Engineering</b>
            <small>ALANDI, PUNE · AUTONOMOUS INSTITUTE</small>
          </div>
        </div>

        <div className="auth-form-wrap">
          <span className="auth-kicker">COLLEGE KNOWLEDGE ASSISTANT</span>
          <h1>
            Student <em>Portal</em>
          </h1>
          <p className="auth-intro">
            Sign in with your student credentials, or continue as a guest to explore admissions,
            fees, examinations, and college regulations.
          </p>

          <form onSubmit={submit}>
            <label htmlFor="student-email">Email address</label>
            <div className="auth-input">
              <Mail size={18} />
              <input
                id="student-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@mitaoe.ac.in or personal email"
                autoComplete="username"
                required
              />
            </div>

            <label htmlFor="student-password">Password</label>
            <div className="auth-input">
              <LockKeyhole size={18} />
              <input
                id="student-password"
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your student password"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShow(!show)}
                aria-label="Toggle password visibility"
              >
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? "Signing in..." : "Sign in as Student"}
              <ArrowRight size={18} />
            </button>
          </form>

          {/* Quick demo credentials hint */}
          <div className="demo-hint-box">
            <span>Testing student mode?</span>
            <button type="button" onClick={fillDemo} className="demo-fill-btn">
              Auto-fill demo credentials
            </button>
          </div>

          <div className="auth-divider">
            <span>OR</span>
          </div>

          {/* Explicit Continue as Guest option */}
          <div className="guest-action-card">
            <div className="guest-action-info">
              <div className="guest-badge">
                <Sparkles size={14} /> GUEST ACCESS
              </div>
              <h3>Explore as Guest</h3>
              <p>
                No account needed. Ask questions about admissions, eligibility, fees,
                placement stats, courses, exams, and hostel facilities.
              </p>
            </div>
            <button
              type="button"
              className="guest-submit-btn"
              onClick={onContinueGuest}
            >
              <UserCheck size={18} />
              Continue as Guest
              <ArrowRight size={16} />
            </button>
          </div>

          <div className="auth-security">
            <ShieldCheck size={18} />
            <span>All responses are grounded in verified, official MITAOE documents.</span>
          </div>
        </div>

        <footer>
          © {new Date().getFullYear()} MIT Academy of Engineering, Pune. All rights reserved.
        </footer>
      </section>
    </main>
  );
}
