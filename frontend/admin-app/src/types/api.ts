export interface HealthStatus { status:string; project_name:string; environment:string; version:string; }
export interface DocumentItem {
 id:string; original_filename:string; normalized_filename:string; file_type:string;
 file_size:number; content_hash:string; document_version:number; status:string;
 chunk_count:number; is_active:boolean; created_at:string; updated_at:string;
 processing_started_at?:string|null; processing_completed_at?:string|null; error_message?:string|null;
}
export interface DocumentListResponse { items:DocumentItem[]; total:number; skip:number; limit:number; }
export interface UploadResponse { message:string; action:string; is_duplicate:boolean; document:DocumentItem; }

export interface ReadinessStatus {
 status:string; qdrant_configured:boolean; qdrant_connected:boolean;
 database_configured:boolean; database_connected:boolean; gemini_configured:boolean;
 gemini_model:string; embedding_provider:string; embedding_model:string;
 embedding_dimension:number; details?:Record<string,string>|null;
}
