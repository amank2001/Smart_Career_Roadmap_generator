"use client";

import { useEffect, useState, useCallback } from "react";
import type { ProjectSuggestion } from "@/types/project";
import {
  getProjectSuggestions,
  skipAllProjects,
  ProjectApiError,
} from "@/lib/api/projects";
import { ProjectCard } from "./ProjectCard";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; projects: ProjectSuggestion[] }
  | { status: "skipped" };

interface ProjectSuggestionsProps {
  planId: string;
}

export function ProjectSuggestions({ planId }: ProjectSuggestionsProps) {
  const [viewState, setViewState] = useState<ViewState>({ status: "idle" });
  const [isSkipping, setIsSkipping] = useState(false);

  const fetchProjects = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const projects = await getProjectSuggestions(planId);
      setViewState({ status: "success", projects });
    } catch (err) {
      if (err instanceof ProjectApiError) {
        setViewState({ status: "error", message: err.message });
      } else {
        setViewState({
          status: "error",
          message: "An unexpected error occurred while loading projects.",
        });
      }
    }
  }, [planId]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  function handleProjectUpdated(updated: ProjectSuggestion) {
    if (viewState.status === "success") {
      setViewState({
        ...viewState,
        projects: viewState.projects.map((p) =>
          p.id === updated.id ? updated : p
        ),
      });
    }
  }

  async function handleSkipAll() {
    setIsSkipping(true);
    try {
      await skipAllProjects(planId);
      setViewState({ status: "skipped" });
    } catch (err) {
      if (err instanceof ProjectApiError) {
        setViewState({ status: "error", message: err.message });
      } else {
        setViewState({
          status: "error",
          message: "An unexpected error occurred.",
        });
      }
    } finally {
      setIsSkipping(false);
    }
  }

  const allDismissedOrCompleted =
    viewState.status === "success" &&
    viewState.projects.length > 0 &&
    viewState.projects.every((p) => p.completed || p.dismissed);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">
          Project Suggestions
        </h2>
        {viewState.status === "success" && !allDismissedOrCompleted && (
          <button
            onClick={handleSkipAll}
            disabled={isSkipping}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Skip all project suggestions"
          >
            {isSkipping ? "Skipping..." : "Skip All Projects"}
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
            <p className="mt-3 text-sm text-gray-600">
              Loading project suggestions...
            </p>
          </div>
        </div>
      )}

      {viewState.status === "error" && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h3 className="text-lg font-semibold text-red-800">Error</h3>
          <p className="mt-2 text-sm text-red-700">{viewState.message}</p>
          <button
            onClick={fetchProjects}
            className="mt-4 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Try Again
          </button>
        </div>
      )}

      {viewState.status === "success" && (
        <div className="space-y-4" aria-label="Project suggestions list">
          {viewState.projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onProjectUpdated={handleProjectUpdated}
            />
          ))}
        </div>
      )}

      {viewState.status === "skipped" && (
        <div
          className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center"
          role="status"
          aria-live="polite"
        >
          <p className="text-sm text-gray-600">
            All projects skipped. You can proceed to the next phase of your roadmap.
          </p>
        </div>
      )}

      {allDismissedOrCompleted && (
        <div
          className="rounded-lg border border-green-200 bg-green-50 p-4 text-center"
          role="status"
          aria-live="polite"
        >
          <p className="text-sm text-green-700">
            All projects handled. You can proceed to the next phase of your roadmap.
          </p>
        </div>
      )}
    </div>
  );
}
