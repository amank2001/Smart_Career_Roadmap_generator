"use client";

import type { WeeklyPlan, PlanStatus } from "@/types/weekly-plan";

interface PlanTimelineProps {
  plans: WeeklyPlan[];
}

const STATUS_STYLES: Record<PlanStatus, { dot: string; line: string; label: string }> = {
  completed: {
    dot: "bg-green-500 border-green-300",
    line: "bg-green-300",
    label: "text-green-700",
  },
  "in-progress": {
    dot: "bg-indigo-500 border-indigo-300 ring-2 ring-indigo-200",
    line: "bg-gray-300",
    label: "text-indigo-700",
  },
  upcoming: {
    dot: "bg-gray-300 border-gray-200",
    line: "bg-gray-200",
    label: "text-gray-500",
  },
};

export function PlanTimeline({ plans }: PlanTimelineProps) {
  if (plans.length === 0) return null;

  return (
    <nav aria-label="Roadmap progress timeline" className="overflow-x-auto">
      <ol className="flex items-center gap-0 py-2">
        {plans.map((plan, idx) => {
          const styles = STATUS_STYLES[plan.status];
          const isLast = idx === plans.length - 1;

          return (
            <li key={plan.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <span
                  className={`h-3 w-3 rounded-full border ${styles.dot}`}
                  aria-label={`Week ${plan.week_number}: ${plan.status}`}
                  title={`Week ${plan.week_number} - ${plan.status}`}
                />
                <span className={`mt-1 text-[10px] font-medium ${styles.label}`}>
                  W{plan.week_number}
                </span>
              </div>
              {!isLast && (
                <div
                  className={`h-0.5 w-6 ${styles.line}`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
