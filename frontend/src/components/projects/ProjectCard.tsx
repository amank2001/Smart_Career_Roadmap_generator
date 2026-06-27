"use client";

import { useState } from "react";
import type { ProjectSuggestion, ProjectComplexity } from "@/types/project";
import { completeProject, dismissProject, ProjectApiError } from "@/lib/api/projects";

const COMPLEXITY_STYLES: Record<ProjectComplexity, string> = {
  beginner: "bg-emerald-100 text-emerald-800",
  intermediate: "bg-amber-100 text-amber-800",
  advanced: "bg-red-100 text-red-800",
};

const COMPLEXITY_LABELS: Record<ProjectComplexity, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

const MAX_OUTCOME_LENGTH = 500;

interface ProjectCardProps {
  project: ProjectSuggestion;
  onProjectUpdated: (updated: ProjectSuggestion) => void;
}

export function ProjectCard({ project, onProjectUpdated }: ProjectCardProps) {
  const [isCompleting, setIsCompleting] = useState(false);
  const [isDismissing, setIsDismissing] = useState(false);
  const [showCompleteForm, setShowCompleteForm] = useState(false);
  const [outcomeText, setOutcomeText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleComplete(e: React.FormEvent) {
    e.preventDefault();
    if (outcomeText.length > MAX_OUTCOME_LENGTH) {
      setError("Outcome description must be 500 characters or fewer");
      return;
    }

    setError(null);
    setIsCompleting(true);
    try {
      const updated = await completeProject(project.id, outcomeText);
      onProjectUpdated(updated);
    } catch (err) {
      if (err instanceof ProjectApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsCompleting(false);
    }
  }

  async function handleDismiss() {
    setError(null);
    setIsDismissing(true);
    try {
      const updated = await dismissProject(project.id);
      onProjectUpdated(updated);
    } catch (err) {
      if (err instanceof ProjectApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsDismissing(false);
    }
  }

  if (project.completed) {
    return (
      <article
        className="rounded-lg border border-green-200 bg-green-50 p-5"
        aria-label={`Completed project: ${project.title}`}
      >
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-base font-semibold text-green-800">
            {project.title}
          </h3>
          <span className="inline-flex items-center rounded-full bg-green-200 px-2 py-0.5 text-xs font-medium text-green-900">
            Completed
          </span>
        </div>
        {project.outcome_description && (
          <p className="mt-2 text-sm text-green-700">
            <span className="font-medium">Outcome:</span> {project.outcome_description}
          </p>
        )}
      </article>
    );
  }

  if (project.dismissed) {
    return (
      <article
        className="rounded-lg border border-gray-200 bg-gray-50 p-5 opacity-60"
        aria-label={`Dismissed project: ${project.title}`}
      >
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-base font-semibold text-gray-500 line-through">
            {project.title}
          </h3>
          <span className="inline-flex items-center rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-600">
            Dismissed
          </span>
        </div>
      </article>
    );
  }

  return (
    <article
      className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
      aria-label={`Project suggestion: ${project.title}`}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base font-semibold text-gray-900">
          {project.title}
        </h3>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${COMPLEXITY_STYLES[project.complexity]}`}
          >
            {COMPLEXITY_LABELS[project.complexity]}
          </span>
          <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
            {project.estimated_weeks} {project.estimated_weeks === 1 ? "week" : "weeks"}
          </span>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <div>
          <h4 className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Objectives
          </h4>
          <ul className="mt-1 space-y-1" aria-label="Project objectives">
            {project.objectives.map((obj, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span aria-hidden="true" className="mt-0.5 text-indigo-400">
                  &#8226;
                </span>
                {obj}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Deliverables
          </h4>
          <ul className="mt-1 space-y-1" aria-label="Project deliverables">
            {project.deliverables.map((del, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span aria-hidden="true" className="mt-0.5 text-green-400">
                  &#10003;
                </span>
                {del}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Technologies
          </h4>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {project.technologies.map((tech, i) => (
              <span
                key={i}
                className="inline-flex rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div
          className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </div>
      )}

      {showCompleteForm ? (
        <form onSubmit={handleComplete} className="mt-4 space-y-3">
          <label
            htmlFor={`outcome-${project.id}`}
            className="block text-sm font-medium text-gray-700"
          >
            Describe your outcome
          </label>
          <textarea
            id={`outcome-${project.id}`}
            value={outcomeText}
            onChange={(e) => setOutcomeText(e.target.value)}
            rows={3}
            maxLength={MAX_OUTCOME_LENGTH}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Briefly describe what you built and what you learned..."
            disabled={isCompleting}
            aria-describedby={`outcome-help-${project.id}`}
          />
          <div
            id={`outcome-help-${project.id}`}
            className="flex justify-between text-xs text-gray-500"
          >
            <span>Max 500 characters</span>
            <span
              className={outcomeText.length > MAX_OUTCOME_LENGTH ? "text-red-600" : ""}
              aria-live="polite"
            >
              {outcomeText.length}/{MAX_OUTCOME_LENGTH}
            </span>
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isCompleting || !outcomeText.trim()}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isCompleting ? "Saving..." : "Mark Complete"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowCompleteForm(false);
                setOutcomeText("");
                setError(null);
              }}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="mt-4 flex gap-3">
          <button
            type="button"
            onClick={() => setShowCompleteForm(true)}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Complete Project
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            disabled={isDismissing}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDismissing ? "Dismissing..." : "Dismiss"}
          </button>
        </div>
      )}
    </article>
  );
}
