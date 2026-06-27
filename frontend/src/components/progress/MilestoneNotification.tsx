"use client";

import { useState } from "react";

interface MilestoneNotificationProps {
  /** Skills that have been fully achieved (all related plans completed) */
  achievedSkills: string[];
}

/**
 * Shows milestone notifications when skill gap milestones are fully achieved.
 * Requirement 8.3: Notify user when a skill gap milestone is achieved.
 */
export function MilestoneNotification({ achievedSkills }: MilestoneNotificationProps) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const visible = achievedSkills.filter((skill) => !dismissed.has(skill));

  if (visible.length === 0) {
    return null;
  }

  function handleDismiss(skill: string) {
    setDismissed((prev) => new Set(prev).add(skill));
  }

  return (
    <div className="space-y-2" role="region" aria-label="Milestone notifications">
      {visible.map((skill) => (
        <div
          key={skill}
          className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
          role="alert"
          aria-live="polite"
        >
          <div className="flex items-center gap-2">
            <span aria-hidden="true" className="text-lg">
              🏆
            </span>
            <p className="text-sm font-medium text-amber-800">
              Milestone achieved: <span className="font-semibold">{skill}</span> gap fully closed!
            </p>
          </div>
          <button
            onClick={() => handleDismiss(skill)}
            className="ml-4 rounded p-1 text-amber-600 hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-500"
            aria-label={`Dismiss ${skill} milestone notification`}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
