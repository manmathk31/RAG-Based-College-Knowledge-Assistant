import { HealthStatus, ChatQueryRequest, ChatQueryResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function sendChatQuery(payload: ChatQueryRequest): Promise<ChatQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Chat query failed with status: ${response.status}`);
  }

  return response.json();
}

