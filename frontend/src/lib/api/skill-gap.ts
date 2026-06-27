import type { SkillGapAnalysis, ApiError } from "@/types/skill-gap";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/skill-gap";

export class SkillGapApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "SkillGapApiError";
  }
}

/**
 * Run skill gap analysis for the authenticated user.
 * POST /api/skill-gap/analyze
 */
export async function runSkillGapAnalysis(): Promise<SkillGapAnalysis> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: jsonAuthHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error: ApiError = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new SkillGapApiError(error.error, error.message);
  }

  return response.json();
}

/**
 * Get the latest skill gap analysis results.
 * GET /api/skill-gap/results
 */
export async function getSkillGapResults(): Promise<SkillGapAnalysis> {
  const response = await fetch(`${API_BASE}/results`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error: ApiError = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new SkillGapApiError(error.error, error.message);
  }

  return response.json();
}
