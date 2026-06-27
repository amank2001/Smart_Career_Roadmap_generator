/**
 * API client for communicating with the backend.
 * All requests are proxied through Next.js rewrites to avoid CORS issues.
 */

import { getToken } from "@/lib/auth";

const API_BASE = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    public userMessage: string
  ) {
    super(userMessage);
    this.name = "ApiError";
  }
}

/**
 * Returns default headers including the Authorization header if a token is stored.
 */
function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorCode = "UNKNOWN_ERROR";
    let userMessage = "An unexpected error occurred.";

    try {
      const body = await response.json();
      // FastAPI error format: { detail: { error: "...", message: "..." } }
      // or { error: "...", message: "..." }
      const detail = body.detail ?? body;
      errorCode = detail.error ?? errorCode;
      userMessage = detail.message ?? userMessage;
    } catch {
      // If we can't parse the body, use generic messages
    }

    throw new ApiError(response.status, errorCode, userMessage);
  }

  return response.json() as Promise<T>;
}

export interface Skill {
  name: string;
  proficiency_level?: string | null;
}

export interface CreateProfileInput {
  current_job_title: string;
  years_of_experience: number;
  skills: Skill[];
}

export interface UpdateProfileInput {
  current_job_title?: string | null;
  years_of_experience?: number | null;
  skills?: Skill[] | null;
}

export interface Profile {
  id: string;
  user_id: string;
  current_job_title: string;
  years_of_experience: number;
  skills: Skill[];
  is_complete: boolean;
}

export interface ResumeAnalysisResult {
  success: boolean;
  extracted_data?: {
    skills?: string[];
    job_history?: string[];
    years_of_experience?: number;
    current_job_title?: string;
  } | null;
  error?: string | null;
}

// Profile API

export async function createProfile(data: CreateProfileInput): Promise<Profile> {
  const response = await fetch(`${API_BASE}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  return handleResponse<Profile>(response);
}

export async function updateProfile(data: UpdateProfileInput): Promise<Profile> {
  const response = await fetch(`${API_BASE}/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  return handleResponse<Profile>(response);
}

export async function getProfile(): Promise<Profile> {
  const response = await fetch(`${API_BASE}/profile`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<Profile>(response);
}

export async function uploadResume(
  file: File,
  onProgress?: (percent: number) => void
): Promise<ResumeAnalysisResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/profile/resume`);

    // Attach auth header
    const token = getToken();
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError(xhr.status, "PARSE_ERROR", "Failed to parse response"));
        }
      } else {
        let errorCode = "UNKNOWN_ERROR";
        let userMessage = "An unexpected error occurred.";
        try {
          const body = JSON.parse(xhr.responseText);
          const detail = body.detail ?? body;
          errorCode = detail.error ?? errorCode;
          userMessage = detail.message ?? userMessage;
        } catch {
          // use defaults
        }
        reject(new ApiError(xhr.status, errorCode, userMessage));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new ApiError(0, "NETWORK_ERROR", "Network error. Please check your connection."));
    });

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}
