import type {
  InterviewSession,
  AnswerFeedback,
  GenerateInterviewRequest,
} from "@/types/interview";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/interview";

export class InterviewApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "InterviewApiError";
  }
}

/**
 * Generate mock interview questions.
 * POST /api/interview/generate
 */
export async function generateInterviewQuestions(
  data?: GenerateInterviewRequest
): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(data ?? {}),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new InterviewApiError(error.error, error.message);
  }

  return response.json();
}

/**
 * Get an interview session with its questions.
 * GET /api/interview/sessions/{sessionId}
 */
export async function getInterviewSession(
  sessionId: string
): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new InterviewApiError(error.error, error.message);
  }

  return response.json();
}

/**
 * Submit an answer for evaluation.
 * POST /api/interview/questions/{questionId}/answer
 */
export async function submitAnswer(
  questionId: string,
  userAnswer: string
): Promise<AnswerFeedback> {
  const response = await fetch(`${API_BASE}/questions/${questionId}/answer`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify({ user_answer: userAnswer }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.detail ?? body ?? { error: "UNKNOWN", message: "An unexpected error occurred" };
    throw new InterviewApiError(error.error, error.message);
  }

  return response.json();
}
