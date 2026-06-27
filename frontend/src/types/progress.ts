/** Status of a weekly plan in the learning roadmap */
export type PlanStatus = "completed" | "in-progress" | "upcoming";

/** Overall progress summary from the backend */
export interface ProgressSummary {
  percentage: number; // 0-100
  completed_plans: number;
  total_plans: number;
  skills_acquired: string[];
}

/** A single entry in the progress timeline */
export interface TimelineEntry {
  week_number: number;
  plan_id: string;
  status: PlanStatus;
  skills: string[];
}

/** Structured error response from the progress API */
export interface ProgressApiErrorResponse {
  error: string;
  message: string;
}
