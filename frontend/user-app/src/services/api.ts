import { getAccessToken } from "./auth";
import type { HealthStatus, ChatRequest, ChatResponse, KnowledgeDoc } from "../types/api";

const API = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data as T;
}

export const fetchHealth = () => request<HealthStatus>("/health");

export const fetchKnowledgeCatalog = () =>
  request<{ documents: KnowledgeDoc[] }>("/chat/knowledge-base");

export const sendChatQuery = (payload: ChatRequest) => {
  const token = getAccessToken();
  return request<ChatResponse>("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
};
