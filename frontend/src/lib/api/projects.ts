import type { ProjectSuggestion } from "@/types/project";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/projects";

export class ProjectApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ProjectApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body;
    const code = detail?.error ?? "UNKNOWN";
    const message = detail?.message ?? "An unexpected error occurred";
    throw new ProjectApiError(code, message);
  }
  return response.json();
}

export interface ProjectSuggestionsResult {
  projects: ProjectSuggestion[];
  /** The plan ID these suggestions belong to (needed for skip-all). */
  planId: string;
}

/**
 * Get project suggestions for the current user's roadmap.
 * GET /api/projects/suggestions
 *
 * The backend automatically picks the best weekly plan (in-progress →
 * upcoming → completed). Returns suggestions and the plan ID used.
 */
export async function getProjectSuggestions(): Promise<ProjectSuggestionsResult> {
  const response = await fetch(`${API_BASE}/suggestions`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });
  const projects = await handleResponse<ProjectSuggestion[]>(response);
  // The plan ID is surfaced via the X-Plan-Id response header set by the backend.
  // Fall back to extracting from the first project if the header is absent.
  const planId = response.headers.get("X-Plan-Id") ?? "";
  return { projects, planId };
}

/**
 * Mark a project as complete with an outcome description.
 * PUT /api/projects/{projectId}/complete
 */
export async function completeProject(
  projectId: string,
  outcome: string
): Promise<ProjectSuggestion> {
  const response = await fetch(`${API_BASE}/${projectId}/complete`, {
    method: "PUT",
    headers: jsonAuthHeaders(),
    body: JSON.stringify({ outcome }),
  });
  return handleResponse<ProjectSuggestion>(response);
}

/**
 * Dismiss a project suggestion.
 * PUT /api/projects/{projectId}/dismiss
 */
export async function dismissProject(
  projectId: string
): Promise<ProjectSuggestion> {
  const response = await fetch(`${API_BASE}/${projectId}/dismiss`, {
    method: "PUT",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<ProjectSuggestion>(response);
}

/**
 * Skip all projects for a milestone.
 * POST /api/projects/skip/{planId}
 */
export async function skipAllProjects(planId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/skip/${planId}`, {
    method: "POST",
    headers: jsonAuthHeaders(),
  });
  await handleResponse<unknown>(response);
}
