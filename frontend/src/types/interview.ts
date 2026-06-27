/** Category types for interview questions */
export type InterviewCategory = "technical" | "behavioral" | "system-design";

/** Difficulty/proficiency level for questions */
export type DifficultyLevel = "beginner" | "intermediate" | "advanced";

/** A single interview question from the backend */
export interface InterviewQuestion {
  id: string;
  question: string;
  category: InterviewCategory;
  difficulty: DifficultyLevel;
  model_answer: string;
  evaluation_criteria: string[];
}

/** An interview session containing multiple questions */
export interface InterviewSession {
  id: string;
  questions: InterviewQuestion[];
  created_at: string;
}

/** Feedback received after submitting an answer */
export interface AnswerFeedback {
  strengths: string[];
  areas_for_improvement: string[];
  overall_assessment: string;
}

/** Request body for generating interview questions */
export interface GenerateInterviewRequest {
  target_role_id?: string;
}

/** Request body for submitting an answer */
export interface SubmitAnswerRequest {
  user_answer: string;
}

/** Response from submitting an answer */
export interface SubmitAnswerResponse {
  feedback: AnswerFeedback;
}
