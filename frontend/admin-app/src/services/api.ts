import { HealthStatus, DocumentItem } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const ADMIN_SECRET = import.meta.env.VITE_ADMIN_API_SECRET || 'dev-admin-secret';

export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    headers: {
      'X-Admin-Secret': ADMIN_SECRET,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch documents with status: ${response.status}`);
  }

  return response.json();
}

