export type ProficiencyLevel = "beginner" | "intermediate" | "advanced";
export type GapCategory = "critical" | "important" | "nice-to-have";

export interface SkillRequirement {
  skill_name: string;
  required_proficiency: ProficiencyLevel;
  category: GapCategory;
}

export interface TargetRole {
  id: string;
  user_id: string;
  role_title: string;
  is_recognized: boolean;
  skills: SkillRequirement[];
}

export interface TargetRoleRequirements {
  role_title: string;
  skills: SkillRequirement[];
  recognized: boolean;
}

export interface CustomRoleInput {
  role_title: string;
  skills: SkillRequirement[];
  responsibilities: string;
}

export interface ApiError {
  error: string;
  message: string;
}
