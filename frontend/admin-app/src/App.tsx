import React, { useState, useEffect } from 'react';
import { ShieldAlert, CheckCircle2, AlertCircle, FileUp, Database } from 'lucide-react';
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
    <div className="min-h-screen bg-slate-100 flex flex-col justify-between">
      {/* Header */}
      <header className="bg-slate-900 text-white shadow-md">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-700 rounded-lg">
              <Database className="w-6 h-6 text-emerald-100" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">College Knowledge Admin</h1>
              <p className="text-xs text-slate-400">Document Management & Ingestion Control</p>
            </div>
          </div>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            Admin App (Port 5174)
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-5xl mx-auto px-6 py-12 flex-1 w-full flex flex-col items-center justify-center">
        <div className="w-full max-w-2xl bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <FileUp className="w-8 h-8" />
          </div>

          <h2 className="text-2xl font-semibold text-slate-800">Admin Panel Scaffold Ready</h2>
          <p className="text-slate-600 mt-2 text-sm">
            This is the administrator-facing document management portal. PDF/DOCX file uploading, selective OCR monitoring,
            and Qdrant ingestion lifecycle controls will be integrated in Milestone 11.
          </p>

          {/* Backend Connection Indicator */}
          <div className="mt-6 p-4 rounded-lg bg-slate-50 border border-slate-200 text-left">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Backend Connection Status</h3>
            {loading && <p className="text-sm text-slate-500 animate-pulse">Querying FastAPI backend...</p>}
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

          {/* Security Banner */}
          <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-left flex items-start space-x-2">
            <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800 leading-relaxed">
              Administrative actions (file uploads and document deletion) require the <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">X-Admin-Secret</code> header.
              Ensure <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">ADMIN_API_SECRET</code> is configured.
            </p>
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

