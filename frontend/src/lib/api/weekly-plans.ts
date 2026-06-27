import type { WeeklyPlan, AdjustDelayResult } from "@/types/weekly-plan";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/weekly-plans";

export class WeeklyPlansApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "WeeklyPlansApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body;
    const code = detail?.error ?? "UNKNOWN";
    const message = detail?.message ?? "An unexpected error occurred";
    throw new WeeklyPlansApiError(code, message);
  }
  return response.json();
}

/**
 * Get all weekly plans for the current roadmap.
 * GET /api/weekly-plans
 */
export async function getWeeklyPlans(): Promise<WeeklyPlan[]> {
  const response = await fetch(API_BASE, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<WeeklyPlan[]>(response);
}

/**
 * Get the current active weekly plan.
 * GET /api/weekly-plans/current
 */
export async function getCurrentWeeklyPlan(): Promise<WeeklyPlan> {
  const response = await fetch(`${API_BASE}/current`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<WeeklyPlan>(response);
}

/**
 * Mark a task as complete.
 * PUT /api/weekly-plans/{planId}/tasks/{taskId}/complete
 */
export async function markTaskComplete(
  planId: string,
  taskId: string
): Promise<WeeklyPlan> {
  const response = await fetch(`${API_BASE}/${planId}/tasks/${taskId}/complete`, {
    method: "PUT",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<WeeklyPlan>(response);
}

/**
 * Adjust remaining plans when there's a delay.
 * POST /api/weekly-plans/adjust
 */
export async function adjustForDelay(): Promise<AdjustDelayResult> {
  const response = await fetch(`${API_BASE}/adjust`, {
    method: "POST",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<AdjustDelayResult>(response);
}
