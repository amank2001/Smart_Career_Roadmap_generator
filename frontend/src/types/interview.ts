/** Category types for interview questions */
export type InterviewCategory = "knowledge" | "behavioral" | "case-study";

/** Difficulty/proficiency level for questions */
export type DifficultyLevel = "beginner" | "intermediate" | "advanced";

/** Feedback received after submitting an answer */
export interface AnswerFeedback {
  strengths: string[];
  areas_for_improvement: string[];
  overall_assessment: string;
}
