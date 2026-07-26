/** Category types for interview questions */
export type InterviewCategory = "knowledge" | "behavioral" | "case-study" | "technical" | "system-design" | string;

/** Difficulty/proficiency level for questions */
export type DifficultyLevel = "beginner" | "intermediate" | "advanced";

/** A single interview question returned by the API */
export interface InterviewQuestion {
  id: string;
  question: string;
  category: InterviewCategory;
  difficulty: DifficultyLevel;
  evaluation_criteria: string[];
  model_answer: string;
}

/** A full interview session containing multiple questions */
export interface InterviewSession {
  id: string;
  created_at: string;
  questions: InterviewQuestion[];
}

/** Feedback received after submitting an answer */
export interface AnswerFeedback {
  strengths: string[];
  areas_for_improvement: string[];
  overall_assessment: string;
}
