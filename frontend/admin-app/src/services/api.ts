import type { HealthStatus, ReadinessStatus, DocumentListResponse, DocumentItem, UploadResponse } from "../types/api";
const API=(import.meta.env.VITE_API_BASE_URL||"http://localhost:8000/api/v1").replace(/\/$/,"");
async function req<T>(path:string,secret:string,init?:RequestInit):Promise<T>{
 const res=await fetch(`${API}${path}`,{...init,headers:{...(init?.headers||{}),"X-Admin-Secret":secret}});
 const data=await res.json().catch(()=>({}));
 if(!res.ok) throw new Error(data.detail||`Request failed (${res.status})`);
 return data as T;
}
export async function fetchHealth():Promise<HealthStatus>{
 const r=await fetch(`${API}/health`); if(!r.ok) throw new Error("Health check failed"); return r.json();
}
export const fetchDocuments=(secret:string,skip=0,limit=100)=>req<DocumentListResponse>(`/documents?skip=${skip}&limit=${limit}`,secret);
export async function uploadDocument(secret:string,file:File):Promise<UploadResponse>{
 const body=new FormData(); body.append("file",file);
 return req<UploadResponse>("/documents",secret,{method:"POST",body});
}
export const deleteDocument=(secret:string,id:string)=>req<{message:string;document_id:string;vectors_deleted:boolean}>(`/documents/${encodeURIComponent(id)}`,secret,{method:"DELETE"});
export async function retryDocument(secret:string,id:string,file:File){
 const body=new FormData(); body.append("file",file);
 return req<{message:string;document:DocumentItem}>(`/documents/${encodeURIComponent(id)}/retry`,secret,{method:"POST",body});
}

export const fetchReadiness=()=>fetch(`${API}/health/ready`).then(async r=>{const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Readiness check failed");return d as ReadinessStatus;});
