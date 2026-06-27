"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getSkillGapResults,
  runSkillGapAnalysis,
  SkillGapApiError,
} from "@/lib/api/skill-gap";
import type { SkillGapAnalysis, SkillGap, GapCategory } from "@/types/skill-gap";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; code: string; message: string }
  | { status: "success"; data: SkillGapAnalysis };

const CATEGORY_ORDER: GapCategory[] = ["critical", "important", "nice-to-have"];

const CATEGORY_LABELS: Record<GapCategory, string> = {
  critical: "Critical",
  important: "Important",
  "nice-to-have": "Nice to Have",
};

const CATEGORY_STYLES: Record<GapCategory, { badge: string; border: string; heading: string }> = {
  critical: {
    badge: "bg-red-100 text-red-800",
    border: "border-red-200",
    heading: "text-red-700",
  },
  important: {
    badge: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-200",
    heading: "text-yellow-700",
  },
  "nice-to-have": {
    badge: "bg-blue-100 text-blue-800",
    border: "border-blue-200",
    heading: "text-blue-700",
  },
};

const PROFICIENCY_LABELS: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

const PREREQUISITE_GUIDANCE: Record<string, string> = {
  INCOMPLETE_PROFILE:
    "Please complete your profile with at least a job title and one skill before running the analysis.",
  NO_TARGET_ROLE:
    "Please select a target role before running gap analysis.",
};

function groupGapsByCategory(gaps: SkillGap[]): Record<GapCategory, SkillGap[]> {
  const grouped: Record<GapCategory, SkillGap[]> = {
    critical: [],
    important: [],
    "nice-to-have": [],
  };

  for (const gap of gaps) {
    if (grouped[gap.category]) {
      grouped[gap.category].push(gap);
    }
  }

  return grouped;
}

function SkillGapCard({ gap }: { gap: SkillGap }) {
  const styles = CATEGORY_STYLES[gap.category];
  const proficiencyText = gap.current_proficiency
    ? PROFICIENCY_LABELS[gap.current_proficiency] ?? gap.current_proficiency
    : "None";

  return (
    <li className="rounded-md border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-gray-900">{gap.skill_name}</h4>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles.badge}`}
        >
          {CATEGORY_LABELS[gap.category]}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-4 text-xs text-gray-600">
        <span>
          Current: <span className="font-medium">{proficiencyText}</span>
        </span>
        <span>
          Required:{" "}
          <span className="font-medium">
            {PROFICIENCY_LABELS[gap.required_proficiency] ?? gap.required_proficiency}
          </span>
        </span>
      </div>
    </li>
  );
}

function CategorySection({
  category,
  gaps,
}: {
  category: GapCategory;
  gaps: SkillGap[];
}) {
  const styles = CATEGORY_STYLES[category];

  if (gaps.length === 0) return null;

  return (
    <section
      aria-labelledby={`category-${category}-heading`}
      className={`rounded-lg border ${styles.border} p-4`}
    >
      <h3
        id={`category-${category}-heading`}
        className={`text-lg font-semibold ${styles.heading}`}
      >
        {CATEGORY_LABELS[category]}{" "}
        <span className="text-sm font-normal text-gray-500">
          ({gaps.length} {gaps.length === 1 ? "gap" : "gaps"})
        </span>
      </h3>
      <ul className="mt-3 space-y-2" aria-label={`${CATEGORY_LABELS[category]} skill gaps`}>
        {gaps.map((gap) => (
          <SkillGapCard key={gap.skill_name} gap={gap} />
        ))}
      </ul>
    </section>
  );
}

function AllRequirementsMetView({
  specializations,
}: {
  specializations: string[] | null;
}) {
  return (
    <div
      className="rounded-lg border border-green-200 bg-green-50 p-6"
      role="status"
      aria-live="polite"
    >
      <h3 className="text-lg font-semibold text-green-800">
        All Requirements Met!
      </h3>
      <p className="mt-2 text-sm text-green-700">
        Your current skills meet all the requirements for your target role.
      </p>
      {specializations && specializations.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-green-800">
            Consider these advanced specialization areas:
          </h4>
          <ul className="mt-2 space-y-1" aria-label="Specialization suggestions">
            {specializations.map((spec) => (
              <li
                key={spec}
                className="flex items-center gap-2 text-sm text-green-700"
              >
                <span aria-hidden="true" className="text-green-500">
                  &#10003;
                </span>
                {spec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PrerequisiteErrorView({
  code,
  message,
}: {
  code: string;
  message: string;
}) {
  const guidance = PREREQUISITE_GUIDANCE[code] ?? message;

  return (
    <div
      className="rounded-lg border border-amber-200 bg-amber-50 p-6"
      role="alert"
      aria-live="assertive"
    >
      <h3 className="text-lg font-semibold text-amber-800">
        Prerequisites Missing
      </h3>
      <p className="mt-2 text-sm text-amber-700">{guidance}</p>
      {code === "INCOMPLETE_PROFILE" && (
        <p className="mt-3 text-sm text-amber-600">
          Go to your profile to add your job title and skills.
        </p>
      )}
      {code === "NO_TARGET_ROLE" && (
        <p className="mt-3 text-sm text-amber-600">
          Select a target role to proceed with the analysis.
        </p>
      )}
    </div>
  );
}

export function SkillGapResults() {
  const [viewState, setViewState] = useState<ViewState>({ status: "idle" });

  const fetchResults = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const data = await getSkillGapResults();
      setViewState({ status: "success", data });
    } catch (error) {
      if (error instanceof SkillGapApiError) {
        setViewState({
          status: "error",
          code: error.code,
          message: error.message,
        });
      } else {
        setViewState({
          status: "error",
          code: "UNKNOWN",
          message: "An unexpected error occurred while loading results.",
        });
      }
    }
  }, []);

  const handleRunAnalysis = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const data = await runSkillGapAnalysis();
      setViewState({ status: "success", data });
    } catch (error) {
      if (error instanceof SkillGapApiError) {
        setViewState({
          status: "error",
          code: error.code,
          message: error.message,
        });
      } else {
        setViewState({
          status: "error",
          code: "UNKNOWN",
          message: "An unexpected error occurred while running the analysis.",
        });
      }
    }
  }, []);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">
          Skill Gap Analysis
        </h2>
        <button
          onClick={handleRunAnalysis}
          disabled={viewState.status === "loading"}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Run skill gap analysis"
        >
          {viewState.status === "loading" ? "Analyzing..." : "Run Analysis"}
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
              Analyzing your skill gaps...
            </p>
          </div>
        </div>
      )}

      {viewState.status === "error" &&
        (viewState.code === "INCOMPLETE_PROFILE" ||
          viewState.code === "NO_TARGET_ROLE") && (
          <PrerequisiteErrorView
            code={viewState.code}
            message={viewState.message}
          />
        )}

      {viewState.status === "error" &&
        viewState.code !== "INCOMPLETE_PROFILE" &&
        viewState.code !== "NO_TARGET_ROLE" && (
          <div
            className="rounded-lg border border-red-200 bg-red-50 p-6"
            role="alert"
          >
            <h3 className="text-lg font-semibold text-red-800">
              Analysis Error
            </h3>
            <p className="mt-2 text-sm text-red-700">{viewState.message}</p>
            <button
              onClick={handleRunAnalysis}
              className="mt-4 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              Try Again
            </button>
          </div>
        )}

      {viewState.status === "success" && viewState.data.all_requirements_met && (
        <AllRequirementsMetView
          specializations={viewState.data.advanced_specializations}
        />
      )}

      {viewState.status === "success" && !viewState.data.all_requirements_met && (
        <div className="space-y-4">
          {CATEGORY_ORDER.map((category) => {
            const grouped = groupGapsByCategory(viewState.data.gaps);
            return (
              <CategorySection
                key={category}
                category={category}
                gaps={grouped[category]}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
