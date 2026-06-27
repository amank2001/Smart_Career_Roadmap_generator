"use client";

import { useEffect, useState, useCallback } from "react";
import { getProgressSummary, getProgressTimeline, ProgressApiError } from "@/lib/api/progress";
import type { ProgressSummary, TimelineEntry } from "@/types/progress";
import { ProgressCircle } from "./ProgressCircle";
import { ProgressTimeline } from "./ProgressTimeline";
import { SkillsAcquired } from "./SkillsAcquired";
import { MilestoneNotification } from "./MilestoneNotification";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; code: string; message: string }
  | { status: "success"; summary: ProgressSummary; timeline: TimelineEntry[] };

/**
 * Progress Dashboard — displays overall progress, timeline, skills acquired, and milestones.
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */
export function ProgressDashboard() {
  const [viewState, setViewState] = useState<ViewState>({ status: "idle" });

  const fetchData = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const [summary, timeline] = await Promise.all([
        getProgressSummary(),
        getProgressTimeline(),
      ]);
      setViewState({ status: "success", summary, timeline });
    } catch (error) {
      if (error instanceof ProgressApiError) {
        setViewState({ status: "error", code: error.code, message: error.message });
      } else {
        setViewState({
          status: "error",
          code: "UNKNOWN",
          message: "An unexpected error occurred while loading progress data.",
        });
      }
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (viewState.status === "idle" || viewState.status === "loading") {
    return (
      <div
        className="flex items-center justify-center py-12"
        role="status"
        aria-live="polite"
      >
        <div className="text-center">
          <div
            className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
            aria-hidden="true"
          />
          <p className="mt-3 text-sm text-gray-600">Loading progress data...</p>
        </div>
      </div>
    );
  }

  if (viewState.status === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6" role="alert">
        <h3 className="text-lg font-semibold text-red-800">
          Unable to Load Progress
        </h3>
        <p className="mt-2 text-sm text-red-700">{viewState.message}</p>
        <button
          onClick={fetchData}
          className="mt-4 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { summary, timeline } = viewState;

  // Determine achieved milestones: skills that appear in completed plans
  // but not in any in-progress or upcoming plan (meaning the skill gap is fully closed)
  const completedSkills = new Set<string>();
  const pendingSkills = new Set<string>();
  for (const entry of timeline) {
    if (entry.status === "completed") {
      entry.skills.forEach((s) => completedSkills.add(s));
    } else {
      entry.skills.forEach((s) => pendingSkills.add(s));
    }
  }
  const achievedMilestones = Array.from(completedSkills).filter(
    (s) => !pendingSkills.has(s)
  );

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-semibold text-gray-800">Progress Dashboard</h2>

      {/* Milestone notifications */}
      <MilestoneNotification achievedSkills={achievedMilestones} />

      {/* Top section: Progress circle + stats */}
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start sm:gap-12">
        <ProgressCircle percentage={summary.percentage} />

        <div className="flex-1 space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center shadow-sm">
              <p className="text-2xl font-bold text-indigo-600">{summary.completed_plans}</p>
              <p className="text-xs text-gray-500">Plans Completed</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center shadow-sm">
              <p className="text-2xl font-bold text-gray-700">{summary.total_plans}</p>
              <p className="text-xs text-gray-500">Total Plans</p>
            </div>
          </div>
          <p className="text-sm text-gray-600">
            {summary.total_plans === 0
              ? "No roadmap generated yet."
              : summary.percentage === 100
              ? "Congratulations! You have completed your learning roadmap."
              : `${summary.total_plans - summary.completed_plans} weekly plans remaining.`}
          </p>
        </div>
      </div>

      {/* Skills Acquired */}
      <section aria-labelledby="skills-acquired-heading">
        <h3 id="skills-acquired-heading" className="mb-3 text-lg font-semibold text-gray-700">
          Skills Acquired
        </h3>
        <SkillsAcquired skills={summary.skills_acquired} />
      </section>

      {/* Timeline */}
      <section aria-labelledby="timeline-heading">
        <h3 id="timeline-heading" className="mb-3 text-lg font-semibold text-gray-700">
          Weekly Plan Timeline
        </h3>
        <ProgressTimeline entries={timeline} />
      </section>
    </div>
  );
}
