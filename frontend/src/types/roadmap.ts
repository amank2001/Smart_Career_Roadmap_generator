/** Types for the resource attached to each roadmap topic */
export type ResourceType = "course" | "book" | "tutorial" | "documentation";

export interface LearningResource {
  title: string;
  type: ResourceType;
  url: string | null;
}

/** A single topic in the learning roadmap */
export interface RoadmapTopic {
  id: string;
  skill_name: string;
  category: "critical" | "important" | "nice-to-have";
  proficiency_target: "beginner" | "intermediate" | "advanced";
  prerequisites: string[];
  resources: LearningResource[];
  estimated_hours: number;
  order: number;
}

/** The full learning roadmap */
export interface LearningRoadmap {
  id: string;
  user_id: string;
  topics: RoadmapTopic[];
  total_weeks: number;
  weekly_study_hours: number;
}

/** Input for generating a roadmap */
export interface GenerateRoadmapInput {
  weekly_study_hours?: number;
}

/** Input for updating weekly study hours */
export interface UpdateWeeklyHoursInput {
  weekly_study_hours: number;
}
