/** Complexity level for project suggestions */
export type ProjectComplexity = "beginner" | "intermediate" | "advanced";

/** A single project suggestion from the backend */
export interface ProjectSuggestion {
  id: string;
  title: string;
  objectives: string[];
  deliverables: string[];
  technologies: string[];
  estimated_weeks: number;
  complexity: ProjectComplexity;
  completed: boolean;
  outcome_description: string | null;
  dismissed: boolean;
}

/** Request body for marking a project complete */
export interface CompleteProjectRequest {
  outcome_description: string;
}

/** Error codes related to projects */
export type ProjectErrorCode = "OUTCOME_TOO_LONG" | "NOT_FOUND" | "UNKNOWN";
