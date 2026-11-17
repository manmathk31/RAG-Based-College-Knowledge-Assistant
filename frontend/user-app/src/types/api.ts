export interface HealthStatus {
  status: string;
  project_name: string;
  environment: string;
  version: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatTurn[];
}

export interface SourceCitation {
  citation_id: string;
  document_id: string;
  document_name: string;
  document_version: number;
  page_number: number | null;
  section: string | null;
  chunk_id: string;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  retrieval_mode: string;
  request_id?: string;
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  category: string;
  version: string;
  pages: number;
  description: string;
  sampleQuestions: string[];
}
