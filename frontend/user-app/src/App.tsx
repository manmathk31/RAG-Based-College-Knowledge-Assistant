import React, { useState, useEffect } from 'react';
import { MessageSquare, CheckCircle2, AlertCircle, Compass } from 'lucide-react';
import { fetchHealth } from './services/api';
import { HealthStatus } from './types/api';

export const App: React.FC = () => {
  const [backendHealth, setBackendHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setBackendHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Header */}
      <header className="bg-indigo-600 text-white shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-700 rounded-lg">
              <MessageSquare className="w-6 h-6 text-indigo-100" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">College Knowledge Assistant</h1>
              <p className="text-xs text-indigo-200">Student Chatbot Portal</p>
            </div>
          </div>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
            User App (Port 5173)
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-4xl mx-auto px-4 py-12 flex-1 w-full flex flex-col items-center justify-center">
        <div className="w-full max-w-xl bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Compass className="w-8 h-8" />
          </div>

          <h2 className="text-2xl font-semibold text-slate-800">Student Chatbot Scaffold Ready</h2>
          <p className="text-slate-600 mt-2 text-sm">
            This is the student-facing conversational interface. Actual chat messaging and grounded source citations
            will be connected in Milestone 10.
          </p>

          {/* Backend Connection Indicator */}
          <div className="mt-6 p-4 rounded-lg bg-slate-50 border border-slate-200 text-left">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Backend Health Connection</h3>
            {loading && <p className="text-sm text-slate-500 animate-pulse">Checking backend connectivity...</p>}
            {error && (
              <div className="flex items-center text-amber-600 text-sm">
                <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>Backend offline or unreachable ({error}). Start FastAPI on port 8000.</span>
              </div>
            )}
            {backendHealth && (
              <div className="flex items-center text-emerald-700 text-sm">
                <CheckCircle2 className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>Connected to FastAPI ({backendHealth.project_name} - {backendHealth.environment})</span>
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-wrap gap-2 justify-center">
            <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs rounded-full font-medium">React 18</span>
            <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs rounded-full font-medium">TypeScript</span>
            <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs rounded-full font-medium">Tailwind CSS</span>
            <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs rounded-full font-medium">Vite</span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-4 bg-white text-center text-xs text-slate-500">
        RAG-Based-College-Knowledge-Assistant &bull; Engineering Foundation Phase
      </footer>
    </div>
  );
};

export default App;

