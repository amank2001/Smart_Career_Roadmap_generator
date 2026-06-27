/** Status of a weekly plan */
export type PlanStatus = "completed" | "in-progress" | "upcoming";

/** A single task within a weekly plan */
export interface WeeklyTask {
  id: string;
  description: string;
  estimated_hours: number;
  skill_name: string;
  completion_criterion: string;
  completed: boolean;
}

/** A weekly plan containing tasks */
export interface WeeklyPlan {
  id: string;
  roadmap_id: string;
  week_number: number;
  status: PlanStatus;
  tasks: WeeklyTask[];
  is_practical_milestone: boolean;
}

/** Result from the delay adjustment endpoint */
export interface AdjustDelayResult {
  plans: WeeklyPlan[];
  message: string;
}
