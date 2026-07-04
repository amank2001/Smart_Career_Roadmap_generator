import type { InterviewSession, AnswerFeedback } from "@/types/interview";
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

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body;
    const code = detail?.error ?? "UNKNOWN";
    const message = detail?.message ?? "An unexpected error occurred";
    throw new InterviewApiError(code, message);
  }
  return response.json();
}

/**
 * Generate mock interview questions.
 * The backend automatically fetches target role and progress from the DB.
 * POST /api/interview/generate
 */
export async function generateInterviewQuestions(): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    // No body needed — backend resolves context from JWT
  });
  return handleResponse<InterviewSession>(response);
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
  return handleResponse<InterviewSession>(response);
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
    body: JSON.stringify({ answer: userAnswer }),  // backend expects "answer"
  });
  return handleResponse<AnswerFeedback>(response);
}
