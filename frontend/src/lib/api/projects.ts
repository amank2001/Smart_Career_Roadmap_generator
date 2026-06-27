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

/**
 * Get project suggestions for a milestone (weekly plan).
 * GET /api/projects/suggestions/{planId}
 */
export async function getProjectSuggestions(
  planId: string
): Promise<ProjectSuggestion[]> {
  const response = await fetch(`${API_BASE}/suggestions/${planId}`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new ProjectApiError(error.error, error.message);
  }

  return response.json();
}

/**
 * Mark a project as complete with an outcome description.
 * PUT /api/projects/{projectId}/complete
 */
export async function completeProject(
  projectId: string,
  outcomeDescription: string
): Promise<ProjectSuggestion> {
  const response = await fetch(`${API_BASE}/${projectId}/complete`, {
    method: "PUT",
    headers: jsonAuthHeaders(),
    body: JSON.stringify({ outcome_description: outcomeDescription }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new ProjectApiError(error.error, error.message);
  }

  return response.json();
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

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new ProjectApiError(error.error, error.message);
  }

  return response.json();
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

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new ProjectApiError(error.error, error.message);
  }
}
