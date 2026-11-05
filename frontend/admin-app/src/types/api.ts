export interface HealthStatus {
  status: string;
  project_name: string;
  environment: string;
  version: string;
}

export type IngestionStatus = 'UPLOADED' | 'PROCESSING' | 'INDEXED' | 'FAILED';

export interface DocumentItem {
  id: string;
  filename: string;
  fileSize: number;
  status: IngestionStatus;
  chunksCount?: number;
  uploadedAt: string;
  errorMessage?: string;
}

