/** Proficiency levels used across the application */
export type ProficiencyLevel = "beginner" | "intermediate" | "advanced";

/** Categories that classify the importance of a skill gap */
export type GapCategory = "critical" | "important" | "nice-to-have";

/** A single identified skill gap */
export interface SkillGap {
  skill_name: string;
  category: GapCategory;
  current_proficiency: ProficiencyLevel | null;
  required_proficiency: ProficiencyLevel;
}

/** Full skill gap analysis result from the backend */
export interface SkillGapAnalysis {
  gaps: SkillGap[];
  all_requirements_met: boolean;
  advanced_specializations: string[] | null;
}

/** Prerequisite error codes returned by the backend */
export type PrerequisiteErrorCode =
  | "INCOMPLETE_PROFILE"
  | "NO_TARGET_ROLE"
  | "MISSING_PREREQUISITE";

/** Structured error response from the API */
export interface ApiError {
  error: string;
  message: string;
}
