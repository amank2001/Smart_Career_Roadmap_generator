"use client";

import type { TimelineEntry, PlanStatus } from "@/types/progress";

interface ProgressTimelineProps {
  entries: TimelineEntry[];
}

const STATUS_STYLES: Record<PlanStatus, { dot: string; line: string; label: string; text: string }> = {
  completed: {
    dot: "bg-green-500",
    line: "bg-green-500",
    label: "Completed",
    text: "text-green-700",
  },
  "in-progress": {
    dot: "bg-indigo-500 ring-4 ring-indigo-100",
    line: "bg-gray-300",
    label: "In Progress",
    text: "text-indigo-700",
  },
  upcoming: {
    dot: "bg-gray-300",
    line: "bg-gray-300",
    label: "Upcoming",
    text: "text-gray-500",
  },
};

/**
 * A vertical timeline showing weekly plan statuses with color-coded indicators.
 * Requirement 8.4: Visual timeline with completed, in-progress, upcoming status.
 */
export function ProgressTimeline({ entries }: ProgressTimelineProps) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-500" role="status">
        No timeline data available. Generate a roadmap to see your progress timeline.
      </p>
    );
  }

  return (
    <div role="list" aria-label="Weekly plan timeline">
      {entries.map((entry, index) => {
        const styles = STATUS_STYLES[entry.status];
        const isLast = index === entries.length - 1;

        return (
          <div key={entry.plan_id} role="listitem" className="relative flex gap-4 pb-6 last:pb-0">
            {/* Vertical line connector */}
            <div className="flex flex-col items-center">
              <div
                className={`h-4 w-4 rounded-full flex-shrink-0 ${styles.dot}`}
                aria-hidden="true"
              />
              {!isLast && (
                <div
                  className={`w-0.5 flex-1 min-h-[24px] ${styles.line}`}
                  aria-hidden="true"
                />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 -mt-0.5">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-medium text-gray-900">
                  Week {entry.week_number}
                </h4>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles.text} bg-opacity-10`}
                  style={{
                    backgroundColor:
                      entry.status === "completed"
                        ? "rgb(220 252 231)"
                        : entry.status === "in-progress"
                        ? "rgb(224 231 255)"
                        : "rgb(243 244 246)",
                  }}
                >
                  {styles.label}
                </span>
              </div>
              {entry.skills.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {entry.skills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
