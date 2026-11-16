export interface Student { id:string; email:string; full_name:string; }
const API=(import.meta.env.VITE_API_BASE_URL||"http://localhost:8000/api/v1").replace(/\/$/,"");
let accessToken:string|null=null;
export const setAccessToken=(token:string|null)=>{accessToken=token;};
export const getAccessToken=()=>accessToken;
async function authRequest<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch(`${API}/auth${path}`,{
  method:body===undefined?"POST":"POST",
  credentials:"include",
  headers:{"Content-Type":"application/json"},
  ...(body===undefined?{}:{body:JSON.stringify(body)})
 });
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(data.detail||"Authentication failed");
 return data as T;
}
export async function loginStudent(email:string,password:string){
 const result=await authRequest<{access_token:string;student:Student}>("/login",{email,password});
 setAccessToken(result.access_token);return result.student;
}
export async function restoreSession(){
 try{
  const result=await authRequest<{access_token:string;student:Student}>("/refresh");
  setAccessToken(result.access_token);return result.student;
 }catch{return null;}
}
export async function logoutStudent(){
 try{await authRequest<{message:string}>("/logout");}finally{setAccessToken(null);}
}
