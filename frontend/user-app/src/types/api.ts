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
  language?: string;
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

export interface ExtractedEntity {
  text: string;
  category: "REGULATION" | "FEE" | "ELIGIBILITY" | "DATE_DEADLINE" | "COURSE" | "PLACEMENT" | "FACILITY" | string;
  confidence?: number;
}

export interface SentimentAspect {
  aspect: string;
  sentiment: string;
  polarity: number;
  snippet: string;
}

export interface SentimentData {
  overall_sentiment: string;
  polarity_score: number;
  aspects?: SentimentAspect[];
  summary?: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  retrieval_mode: string;
  request_id?: string;
  language?: string;
  topics?: string[];
  entities?: ExtractedEntity[];
  sentiment?: SentimentData;
}
