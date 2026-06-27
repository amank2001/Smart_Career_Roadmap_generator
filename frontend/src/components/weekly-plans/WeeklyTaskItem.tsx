"use client";

import type { WeeklyTask } from "@/types/weekly-plan";

interface WeeklyTaskItemProps {
  task: WeeklyTask;
  onComplete: (taskId: string) => void;
  isCompleting: boolean;
  disabled: boolean;
}

export function WeeklyTaskItem({
  task,
  onComplete,
  isCompleting,
  disabled,
}: WeeklyTaskItemProps) {
  return (
    <li
      className={`rounded-md border p-3 transition-colors ${
        task.completed
          ? "border-green-200 bg-green-50"
          : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 pt-0.5">
          <input
            type="checkbox"
            checked={task.completed}
            onChange={() => onComplete(task.id)}
            disabled={task.completed || isCompleting || disabled}
            aria-label={`Mark "${task.description}" as complete`}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
        <div className="flex-1 min-w-0">
          <p
            className={`text-sm font-medium ${
              task.completed ? "text-gray-500 line-through" : "text-gray-900"
            }`}
          >
            {task.description}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
            <span>{task.estimated_hours}h</span>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600">
              {task.skill_name}
            </span>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            <span className="font-medium">Completion:</span>{" "}
            {task.completion_criterion}
          </p>
        </div>
      </div>
    </li>
  );
}
