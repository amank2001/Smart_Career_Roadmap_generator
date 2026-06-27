"use client";

import { useState, useCallback } from "react";
import type { WeeklyPlan } from "@/types/weekly-plan";
import { WeeklyTaskItem } from "./WeeklyTaskItem";

interface WeeklyPlanCardProps {
  plan: WeeklyPlan;
  onTaskComplete: (planId: string, taskId: string) => Promise<void>;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  completed: { bg: "bg-green-50", text: "text-green-800", dot: "bg-green-500" },
  "in-progress": { bg: "bg-indigo-50", text: "text-indigo-800", dot: "bg-indigo-500" },
  upcoming: { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400" },
};

const STATUS_LABELS: Record<string, string> = {
  completed: "Completed",
  "in-progress": "In Progress",
  upcoming: "Upcoming",
};

export function WeeklyPlanCard({ plan, onTaskComplete }: WeeklyPlanCardProps) {
  const [completingTaskId, setCompletingTaskId] = useState<string | null>(null);
  const styles = STATUS_STYLES[plan.status] ?? STATUS_STYLES.upcoming;
  const isDisabled = plan.status !== "in-progress";

  const handleComplete = useCallback(
    async (taskId: string) => {
      setCompletingTaskId(taskId);
      try {
        await onTaskComplete(plan.id, taskId);
      } finally {
        setCompletingTaskId(null);
      }
    },
    [plan.id, onTaskComplete]
  );

  const completedCount = plan.tasks.filter((t) => t.completed).length;
  const totalTasks = plan.tasks.length;

  return (
    <article
      className={`rounded-lg border border-gray-200 ${styles.bg} p-4`}
      aria-label={`Week ${plan.week_number} plan`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">
            Week {plan.week_number}
          </h3>
          {plan.is_practical_milestone && (
            <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
              Milestone
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`flex items-center gap-1.5 text-xs font-medium ${styles.text}`}>
            <span className={`h-2 w-2 rounded-full ${styles.dot}`} aria-hidden="true" />
            {STATUS_LABELS[plan.status]}
          </span>
          <span className="text-xs text-gray-500">
            {completedCount}/{totalTasks} tasks
          </span>
        </div>
      </div>

      {plan.status === "in-progress" && (
        <div className="mt-2">
          <div className="h-1.5 w-full rounded-full bg-gray-200" role="progressbar" aria-valuenow={completedCount} aria-valuemin={0} aria-valuemax={totalTasks} aria-label={`${completedCount} of ${totalTasks} tasks completed`}>
            <div
              className="h-1.5 rounded-full bg-indigo-500 transition-all"
              style={{ width: `${totalTasks > 0 ? (completedCount / totalTasks) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      <ul className="mt-3 space-y-2" aria-label={`Tasks for week ${plan.week_number}`}>
        {plan.tasks.map((task) => (
          <WeeklyTaskItem
            key={task.id}
            task={task}
            onComplete={handleComplete}
            isCompleting={completingTaskId === task.id}
            disabled={isDisabled}
          />
        ))}
      </ul>
    </article>
  );
}
