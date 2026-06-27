import type { ProgressSummary, TimelineEntry, ProgressApiErrorResponse } from "@/types/progress";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/progress";

export class ProgressApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ProgressApiError";
  }
}

/**
 * Get overall progress summary for the authenticated user.
 * GET /api/progress
 */
export async function getProgressSummary(): Promise<ProgressSummary> {
  const response = await fetch(API_BASE, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error: ProgressApiErrorResponse = body?.detail ?? body ?? {
      error: "UNKNOWN",
      message: "An unexpected error occurred",
    };
    throw new ProgressApiError(error.error, error.message);
  }

  return response.json();
}

/**
 * Get the visual timeline data showing weekly plan statuses.
 * GET /api/progress/timeline
 */
export async function getProgressTimeline(): Promise<TimelineEntry[]> {
  const response = await fetch(`${API_BASE}/timeline`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error: ProgressApiErrorResponse = body?.detail ?? body ?? {
      error: "UNKNOWN",
      message: "An unexpected error occurred",
    };
    throw new ProgressApiError(error.error, error.message);
  }

  return response.json();
}
