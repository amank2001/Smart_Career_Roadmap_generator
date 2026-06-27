"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getWeeklyPlans,
  markTaskComplete,
  adjustForDelay,
  WeeklyPlansApiError,
} from "@/lib/api/weekly-plans";
import type { WeeklyPlan } from "@/types/weekly-plan";
import { WeeklyPlanCard } from "./WeeklyPlanCard";
import { PlanTimeline } from "./PlanTimeline";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; code: string; message: string }
  | { status: "success"; data: WeeklyPlan[] };

export function WeeklyPlansView() {
  const [viewState, setViewState] = useState<ViewState>({ status: "idle" });
  const [showDelayPrompt, setShowDelayPrompt] = useState(false);
  const [isAdjusting, setIsAdjusting] = useState(false);

  const fetchPlans = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const data = await getWeeklyPlans();
      setViewState({ status: "success", data });
    } catch (error) {
      if (error instanceof WeeklyPlansApiError) {
        setViewState({ status: "error", code: error.code, message: error.message });
      } else {
        setViewState({
          status: "error",
          code: "UNKNOWN",
          message: "An unexpected error occurred while loading weekly plans.",
        });
      }
    }
  }, []);

  const handleTaskComplete = useCallback(
    async (planId: string, taskId: string) => {
      try {
        const updatedPlan = await markTaskComplete(planId, taskId);
        setViewState((prev) => {
          if (prev.status !== "success") return prev;
          const updatedPlans = prev.data.map((p) =>
            p.id === updatedPlan.id ? updatedPlan : p
          );
          return { status: "success", data: updatedPlans };
        });
      } catch (error) {
        if (error instanceof WeeklyPlansApiError) {
          // Show error inline but don't disrupt the view
          console.error("Failed to mark task complete:", error.message);
        }
      }
    },
    []
  );

  const handleShowDelayPrompt = useCallback(() => {
    setShowDelayPrompt(true);
  }, []);

  const handleAdjustDelay = useCallback(async () => {
    setIsAdjusting(true);
    try {
      const result = await adjustForDelay();
      setViewState({ status: "success", data: result.plans });
      setShowDelayPrompt(false);
    } catch (error) {
      if (error instanceof WeeklyPlansApiError) {
        console.error("Failed to adjust plans:", error.message);
      }
    } finally {
      setIsAdjusting(false);
    }
  }, []);

  const handleDismissDelayPrompt = useCallback(() => {
    setShowDelayPrompt(false);
  }, []);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const completedPlans =
    viewState.status === "success"
      ? viewState.data.filter((p) => p.status === "completed").length
      : 0;
  const totalPlans =
    viewState.status === "success" ? viewState.data.length : 0;
  const allCompleted =
    viewState.status === "success" &&
    totalPlans > 0 &&
    completedPlans === totalPlans;
  const currentPlan =
    viewState.status === "success"
      ? viewState.data.find((p) => p.status === "in-progress")
      : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">Weekly Plans</h2>
        {currentPlan && (
          <button
            onClick={handleShowDelayPrompt}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            aria-label="Report a delay in your progress"
          >
            Report Delay
          </button>
        )}
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
            <p className="mt-3 text-sm text-gray-600">Loading weekly plans...</p>
          </div>
        </div>
      )}

      {viewState.status === "error" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6" role="alert">
          <h3 className="text-lg font-semibold text-red-800">Error</h3>
          <p className="mt-2 text-sm text-red-700">{viewState.message}</p>
          <button
            onClick={fetchPlans}
            className="mt-4 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Try Again
          </button>
        </div>
      )}

      {viewState.status === "success" && (
        <>
          {/* Timeline */}
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="mb-2 text-sm font-medium text-gray-700">Progress Timeline</h3>
            <PlanTimeline plans={viewState.data} />
            <p className="mt-2 text-xs text-gray-500">
              {completedPlans} of {totalPlans} weeks completed
            </p>
          </div>

          {/* Delay Adjustment Prompt */}
          {showDelayPrompt && (
            <div
              className="rounded-lg border border-amber-200 bg-amber-50 p-4"
              role="dialog"
              aria-label="Delay adjustment"
            >
              <h3 className="text-sm font-semibold text-amber-800">
                Adjust for Delay?
              </h3>
              <p className="mt-1 text-sm text-amber-700">
                If you&apos;re behind schedule, we can redistribute remaining tasks across your upcoming weeks.
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={handleAdjustDelay}
                  disabled={isAdjusting}
                  className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:opacity-50"
                >
                  {isAdjusting ? "Adjusting..." : "Adjust Plans"}
                </button>
                <button
                  onClick={handleDismissDelayPrompt}
                  className="rounded-md border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-amber-700 hover:bg-amber-50 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Roadmap Completion Summary */}
          {allCompleted && (
            <div
              className="rounded-lg border border-green-200 bg-green-50 p-6"
              role="status"
              aria-live="polite"
            >
              <h3 className="text-lg font-semibold text-green-800">
                Roadmap Complete!
              </h3>
              <p className="mt-2 text-sm text-green-700">
                Congratulations! You&apos;ve completed all {totalPlans} weeks of your learning roadmap. Your skills have been updated to reflect your progress.
              </p>
            </div>
          )}

          {/* Weekly Plan Cards */}
          <div className="space-y-4">
            {viewState.data.map((plan) => (
              <WeeklyPlanCard
                key={plan.id}
                plan={plan}
                onTaskComplete={handleTaskComplete}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
