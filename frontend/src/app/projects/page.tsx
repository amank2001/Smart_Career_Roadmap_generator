"use client";

import { useState, useEffect } from "react";
import { ProjectSuggestions } from "@/components/projects/ProjectSuggestions";

/**
 * Projects page — shows project suggestions for the current active weekly plan.
 * In a full implementation, this would fetch the current plan ID from the backend.
 * For now, it uses a placeholder plan ID to demonstrate the UI.
 */
export default function ProjectsPage() {
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching the active plan ID
    // In production, this would call an API to get the current weekly plan
    async function fetchActivePlan() {
      try {
        const response = await fetch("/api/weekly-plans/active");
        if (response.ok) {
          const data = await response.json();
          setActivePlanId(data.id);
        }
      } catch {
        // If no active plan, show guidance
      } finally {
        setIsLoading(false);
      }
    }
    fetchActivePlan();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
        <div className="text-center">
          <div
            className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
            aria-hidden="true"
          />
          <p className="mt-3 text-sm text-gray-600">Loading projects...</p>
        </div>
      </div>
    );
  }

  if (!activePlanId) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-semibold text-gray-800">Project Suggestions</h2>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-sm text-gray-600">
            No active weekly plan found. Complete your roadmap and weekly plans first
            to get personalized project suggestions.
          </p>
          <a
            href="/weekly-plans"
            className="mt-4 inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Go to Weekly Plans
          </a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProjectSuggestions planId={activePlanId} />
    </div>
  );
}
