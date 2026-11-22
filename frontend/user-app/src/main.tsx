import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Login from "./components/Login";
import { loginStudent, logoutStudent, restoreSession, setAccessToken, type Student } from "./services/auth";
import "./index.css";

function Root() {
  const [student, setStudent] = useState<Student | null>(null);
  const [isGuest, setIsGuest] = useState<boolean>(() => {
    try {
      return sessionStorage.getItem("mitaoe_guest_entry") === "true";
    } catch {
      return false;
    }
  });
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [checkingSession, setCheckingSession] = useState<boolean>(true);

  useEffect(() => {
    let active = true;
    restoreSession()
      .then((s) => {
        if (active && s) {
          setStudent(s);
          setIsGuest(false);
        }
      })
      .finally(() => {
        if (active) setCheckingSession(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSignIn = async (email: string, password: string) => {
    const s = await loginStudent(email, password);
    setStudent(s);
    setIsGuest(false);
    setShowLoginModal(false);
    try {
      sessionStorage.removeItem("mitaoe_guest_entry");
    } catch { }
  };

  const handleContinueAsGuest = () => {
    setIsGuest(true);
    setStudent(null);
    setShowLoginModal(false);
    try {
      sessionStorage.setItem("mitaoe_guest_entry", "true");
    } catch { }
  };

  const handleSignOut = async () => {
    try {
      await logoutStudent();
    } finally {
      setAccessToken(null);
      setStudent(null);
      setIsGuest(false);
      try {
        sessionStorage.removeItem("mitaoe_guest_entry");
      } catch { }
    }
  };

  if (checkingSession) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner" />
        <p>Connecting to MITAOE Knowledge Assistant...</p>
      </div>
    );
  }

  // If user is neither signed in nor chose guest access, show Sign In landing page upfront
  const showLanding = !student && !isGuest;

  if (showLanding) {
    return (
      <Login
        onLogin={handleSignIn}
        onContinueGuest={handleContinueAsGuest}
      />
    );
  }

  return (
    <>
      <App
        student={student}
        isGuest={!student}
        onOpenLogin={() => setShowLoginModal(true)}
        onSignOut={handleSignOut}
      />

      {/* Modal overlay if guest clicks "Student Sign In" while in chat */}
      {showLoginModal && (
        <div className="login-overlay">
          <button
            className="login-close"
            onClick={() => setShowLoginModal(false)}
            aria-label="Close sign in and continue as guest"
          >
            ✕ Continue as guest
          </button>
          <Login
            onLogin={handleSignIn}
            onContinueGuest={() => setShowLoginModal(false)}
            isOverlay
          />
        </div>
      )}
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
