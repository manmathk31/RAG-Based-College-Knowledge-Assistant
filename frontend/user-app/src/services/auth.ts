export interface Student {
  id: string;
  email: string;
  full_name: string;
}

const API = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    try {
      localStorage.setItem("mitaoe_access_token", token);
    } catch { }
  } else {
    try {
      localStorage.removeItem("mitaoe_access_token");
      localStorage.removeItem("mitaoe_student_profile");
    } catch { }
  }
};

export const getAccessToken = () => {
  if (!accessToken) {
    try {
      accessToken = localStorage.getItem("mitaoe_access_token");
    } catch { }
  }
  return accessToken;
};

async function authRequest<T>(path: string, body?: unknown): Promise<T> {
  const token = getAccessToken();
  const response = await fetch(`${API}/auth${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Authentication failed");
  return data as T;
}

export async function loginStudent(email: string, password: string): Promise<Student> {
  const result = await authRequest<{ access_token: string; student: Student }>("/login", {
    email,
    password,
  });
  setAccessToken(result.access_token);
  try {
    localStorage.setItem("mitaoe_student_profile", JSON.stringify(result.student));
  } catch { }
  return result.student;
}

export async function restoreSession(): Promise<Student | null> {
  // 1. Try refresh cookie
  try {
    const result = await authRequest<{ access_token: string; student: Student }>("/refresh");
    setAccessToken(result.access_token);
    try {
      localStorage.setItem("mitaoe_student_profile", JSON.stringify(result.student));
    } catch { }
    return result.student;
  } catch {
    // 2. Fallback to localStorage access token if valid
    try {
      const storedToken = localStorage.getItem("mitaoe_access_token");
      const storedProfile = localStorage.getItem("mitaoe_student_profile");
      if (storedToken && storedProfile) {
        setAccessToken(storedToken);
        const res = await fetch(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          return data.student as Student;
        }
      }
    } catch { }
    setAccessToken(null);
    return null;
  }
}

export async function logoutStudent(): Promise<void> {
  try {
    await authRequest<{ message: string }>("/logout");
  } catch {
    // ignore
  } finally {
    setAccessToken(null);
  }
}
