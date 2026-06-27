"use client";

import { useEffect, useState, useCallback } from "react";
import { getRoadmap, generateRoadmap, updateWeeklyHours, RoadmapApiError } from "@/lib/api/roadmap";
import type { LearningRoadmap } from "@/types/roadmap";
import { RoadmapTopicCard } from "./RoadmapTopicCard";
import { WeeklyHoursInput } from "./WeeklyHoursInput";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; code: string; message: string }
  | { status: "success"; data: LearningRoadmap };

export function LearningRoadmapView() {
  const [viewState, setViewState] = useState<ViewState>({ status: "idle" });
  const [isUpdatingHours, setIsUpdatingHours] = useState(false);

  const fetchRoadmap = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const data = await getRoadmap();
      setViewState({ status: "success", data });
    } catch (error) {
      if (error instanceof RoadmapApiError) {
        setViewState({ status: "error", code: error.code, message: error.message });
      } else {
        setViewState({
          status: "error",
          code: "UNKNOWN",
          message: "An unexpected error occurred while loading the roadmap.",
        });
      }
    }
  }, []);

  const handleGenerate = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const data = await generateRoadmap();
      setViewState({ status: "success", data });
    } catch (error) {
      if (error instanceof RoadmapApiError) {
        setViewState({ status: "error", code: error.code, message: error.message });
      } else {
        setViewState({
          status: "error",
          code: "UNKNOWN",
          message: "An unexpected error occurred while generating the roadmap.",
        });
      }
    }
  }, []);

  const handleHoursChange = useCallback(async (hours: number) => {
    setIsUpdatingHours(true);
    try {
      const data = await updateWeeklyHours({ weekly_study_hours: hours });
      setViewState({ status: "success", data });
    } catch (error) {
      if (error instanceof RoadmapApiError) {
        setViewState({ status: "error", code: error.code, message: error.message });
      }
    } finally {
      setIsUpdatingHours(false);
    }
  }, []);

  useEffect(() => {
    fetchRoadmap();
  }, [fetchRoadmap]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">
          Learning Roadmap
        </h2>
        <button
          onClick={handleGenerate}
          disabled={viewState.status === "loading"}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Generate learning roadmap"
        >
          {viewState.status === "loading" ? "Generating..." : "Generate Roadmap"}
        </button>
      </div>

      {viewState.status === "loading" && (
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
            <p className="mt-3 text-sm text-gray-600">
              Building your learning roadmap...
            </p>
          </div>
        </div>
      )}

      {viewState.status === "error" && viewState.code === "NO_GAP_ANALYSIS" && (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 p-6"
          role="alert"
          aria-live="assertive"
        >
          <h3 className="text-lg font-semibold text-amber-800">
            Prerequisite Missing
          </h3>
          <p className="mt-2 text-sm text-amber-700">
            Please run a skill gap analysis first before generating a roadmap.
          </p>
        </div>
      )}

      {viewState.status === "error" && viewState.code !== "NO_GAP_ANALYSIS" && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h3 className="text-lg font-semibold text-red-800">Error</h3>
          <p className="mt-2 text-sm text-red-700">{viewState.message}</p>
          <button
            onClick={handleGenerate}
            className="mt-4 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Try Again
          </button>
        </div>
      )}

      {viewState.status === "success" && (
        <div className="space-y-6">
          <div className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-gray-700">
              {viewState.data.topics.length} topics &middot; {viewState.data.total_weeks} weeks estimated
            </div>
            <WeeklyHoursInput
              currentHours={viewState.data.weekly_study_hours}
              onHoursChange={handleHoursChange}
              isUpdating={isUpdatingHours}
            />
          </div>

          <div className="space-y-3">
            {viewState.data.topics.map((topic, idx) => (
              <RoadmapTopicCard key={topic.id} topic={topic} index={idx} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
