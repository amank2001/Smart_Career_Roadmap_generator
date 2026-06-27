/**
 * Authentication utilities — token storage, login, register, and logout.
 */

const TOKEN_KEY = "career_roadmap_token";

// --- Token storage ---

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

// --- Auth API calls ---

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export class AuthError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "AuthError";
  }
}

async function handleAuthResponse(response: Response): Promise<AuthResponse> {
  if (!response.ok) {
    let code = "UNKNOWN";
    let message = "An unexpected error occurred.";
    try {
      const body = await response.json();
      const detail = body.detail ?? body;
      code = detail.error ?? code;
      message = detail.message ?? message;
    } catch {
      // use defaults
    }
    throw new AuthError(response.status, code, message);
  }
  return response.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await handleAuthResponse(response);
  setToken(data.access_token);
  return data;
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await handleAuthResponse(response);
  setToken(data.access_token);
  return data;
}

export function logout(): void {
  clearToken();
}
