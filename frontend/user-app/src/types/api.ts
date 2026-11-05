export interface HealthStatus {
  status: string;
  project_name: string;
  environment: string;
  version: string;
}

export interface Citation {
  documentName: string;
  pageNumber: number;
  snippet: string;
}

export interface ChatQueryRequest {
  question: string;
}

export interface ChatQueryResponse {
  answer: string;
  sources: Citation[];
}

