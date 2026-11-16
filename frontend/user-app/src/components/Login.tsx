import { useState, type FormEvent } from "react";
import { GraduationCap, Mail, LockKeyhole, Eye, EyeOff, ArrowRight, ShieldCheck } from "lucide-react";
import "./Login.css";

export default function Login({onLogin}:{onLogin:(email:string,password:string)=>Promise<void>}){
 const [email,setEmail]=useState("");const [password,setPassword]=useState("");
 const [show,setShow]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const submit=async(e:FormEvent)=>{e.preventDefault();setBusy(true);setError("");try{await onLogin(email.trim().toLowerCase(),password);}catch(err){setError(err instanceof Error?err.message:"Sign in failed.");}finally{setBusy(false);}};
 return <main className="auth-page">
  <section className="auth-left">
   <div className="auth-brand"><div className="auth-logo"><GraduationCap size={29}/></div><div><b>MIT Academy of Engineering</b><small>ALANDI, PUNE</small></div></div>
   <div className="auth-form-wrap">
    <span className="auth-kicker">OPTIONAL STUDENT SIGN-IN</span><h1>Welcome<br/><em>Back!</em></h1>
    <p className="auth-intro">Optional sign-in for existing MITAOE students. Visitors and prospective students can use the assistant without an account.</p>
    <form onSubmit={submit}>
     <label>Email address</label><div className="auth-input"><Mail size={18}/><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Personal or college email" autoComplete="username" required/></div>
     <label>Password</label><div className="auth-input"><LockKeyhole size={18}/><input type={show?"text":"password"} value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" required/><button type="button" onClick={()=>setShow(!show)} aria-label="Toggle password">{show?<EyeOff size={18}/>:<Eye size={18}/>}</button></div>
     {error&&<div className="auth-error" role="alert">{error}</div>}
     <button className="auth-submit" disabled={busy}>{busy?"Signing in…":"Sign in"}<ArrowRight size={18}/></button>
    </form>
    <div className="auth-security"><ShieldCheck size={18}/> Student sign-in is optional. You can close this window and continue as a guest.</div>
   </div>
   <footer>© {new Date().getFullYear()} MIT Academy of Engineering</footer>
  </section>
  <section className="auth-right"><div className="auth-copy"><span>COLLEGE KNOWLEDGE ASSISTANT</span><h2>Your College.<br/>Your Knowledge.<br/><b>One Intelligent Assistant.</b></h2><p>Explore admissions, programmes, eligibility, fees, placements, campus facilities and academic information. No login is needed for public college information.</p><div><ShieldCheck/> Verified college information</div><div><GraduationCap/> Support for students and future applicants</div><div><LockKeyhole/> Protected student access</div></div></section>
 </main>;
}
