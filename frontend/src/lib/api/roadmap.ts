import type {
  LearningRoadmap,
  GenerateRoadmapInput,
  UpdateWeeklyHoursInput,
} from "@/types/roadmap";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/roadmap";

export class RoadmapApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "RoadmapApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body;
    const code = detail?.error ?? "UNKNOWN";
    const message = detail?.message ?? "An unexpected error occurred";
    throw new RoadmapApiError(code, message);
  }
  return response.json();
}

/**
 * Generate a learning roadmap from the skill gap analysis.
 * POST /api/roadmap/generate
 */
export async function generateRoadmap(
  data?: GenerateRoadmapInput
): Promise<LearningRoadmap> {
  const response = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(data ?? {}),
  });
  return handleResponse<LearningRoadmap>(response);
}

/**
 * Get the current learning roadmap.
 * GET /api/roadmap
 */
export async function getRoadmap(): Promise<LearningRoadmap> {
  const response = await fetch(API_BASE, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<LearningRoadmap>(response);
}

/**
 * Update weekly study hours and recalculate timeline.
 * PUT /api/roadmap/hours
 */
export async function updateWeeklyHours(
  data: UpdateWeeklyHoursInput
): Promise<LearningRoadmap> {
  const response = await fetch(`${API_BASE}/hours`, {
    method: "PUT",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<LearningRoadmap>(response);
}
