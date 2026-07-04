"use client";

import { useState, useEffect } from "react";
import type { SkillRequirement, TargetRole } from "@/types/target-role";
import { SkillRequirementsList } from "./SkillRequirementsList";
import { CustomRoleForm } from "./CustomRoleForm";
import { validateRoleTitle } from "@/lib/validation";
import {
  setTargetRole,
  getTargetRoleRequirements,
  updateTargetRoleSkills,
  setCustomRole,
  TargetRoleApiError,
} from "@/lib/api/target-role";
import { useAppData } from "@/context/AppDataContext";

type FlowState =
  | "loading-existing"  // Checking for a saved role
  | "saved"             // A role is already saved — show summary
  | "input"             // Entering role title
  | "loading"           // Fetching requirements
  | "recognized"        // Role recognized, showing skills
  | "unrecognized"      // Role not recognized, showing custom form
  | "success";          // Role saved successfully

export function TargetRoleSelection() {
  const { targetRole, isLoadingTargetRole, refreshTargetRole } = useAppData();

  const [flowState, setFlowState] = useState<FlowState>("loading-existing");
  const [roleTitle, setRoleTitle] = useState("");
  const [roleTitleError, setRoleTitleError] = useState<string | null>(null);
  const [skills, setSkills] = useState<SkillRequirement[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedRole, setSavedRole] = useState<TargetRole | null>(null);

  // Sync with context — when the context finishes loading, decide what to show
  useEffect(() => {
    if (isLoadingTargetRole) {
      setFlowState("loading-existing");
      return;
    }
    if (targetRole) {
      setSavedRole(targetRole);
      setFlowState("saved");
    } else {
      setFlowState("input");
    }
  }, [targetRole, isLoadingTargetRole]);

  async function handleSearchRole(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);

    const error = validateRoleTitle(roleTitle);
    if (error) {
      setRoleTitleError(error);
      return;
    }
    setRoleTitleError(null);
    setFlowState("loading");

    try {
      const requirements = await getTargetRoleRequirements(roleTitle.trim());

      if (requirements.recognized) {
        setSkills(requirements.skills);
        setFlowState("recognized");
      } else {
        setFlowState("unrecognized");
      }
    } catch (err) {
      if (err instanceof TargetRoleApiError) {
        setApiError(err.message);
      } else {
        setApiError("An unexpected error occurred. Please try again.");
      }
      setFlowState("input");
    }
  }

  async function handleSaveRecognizedRole() {
    setApiError(null);
    setIsSubmitting(true);

    try {
      await setTargetRole(roleTitle.trim());
      const updated = await updateTargetRoleSkills(skills);
      setSavedRole(updated);
      await refreshTargetRole();
      setFlowState("success");
    } catch (err) {
      if (err instanceof TargetRoleApiError) {
        setApiError(err.message);
      } else {
        setApiError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSaveCustomRole(
    customSkills: SkillRequirement[],
    responsibilities: string
  ) {
    setApiError(null);
    setIsSubmitting(true);

    try {
      const role = await setCustomRole({
        role_title: roleTitle.trim(),
        skills: customSkills,
        responsibilities,
      });
      setSavedRole(role);
      await refreshTargetRole();
      setFlowState("success");
    } catch (err) {
      if (err instanceof TargetRoleApiError) {
        setApiError(err.message);
      } else {
        setApiError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleStartEditing() {
    setFlowState("input");
    setRoleTitle("");
    setSkills([]);
    setApiError(null);
    setRoleTitleError(null);
  }

  function handleReset() {
    setFlowState("input");
    setRoleTitle("");
    setSkills([]);
    setApiError(null);
    setRoleTitleError(null);
    setSavedRole(null);
  }

  // Loading spinner while we check for a saved role
  if (flowState === "loading-existing") {
    return (
      <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
        <div className="text-center">
          <div
            className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
            aria-hidden="true"
          />
          <p className="mt-3 text-sm text-gray-600">Loading your target role...</p>
        </div>
      </div>
    );
  }

  // Show saved role summary
  if (flowState === "saved" && savedRole) {
    return (
      <div className="space-y-6">
        <div className="rounded-lg border border-green-200 bg-green-50 p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-green-800">Target Role</h2>
              <p className="mt-1 text-sm text-green-700">
                Your target role is set and ready for skill gap analysis.
              </p>
            </div>
            <button
              type="button"
              onClick={handleStartEditing}
              className="rounded-md border border-green-300 bg-white px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
              Change Role
            </button>
          </div>
        </div>

        {/* Role details card */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Role Title
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {savedRole.role_title}
              </p>
            </div>
            {!savedRole.is_recognized && (
              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                Custom Role
              </span>
            )}
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Required Skills ({savedRole.skills.length})
            </p>
            {savedRole.skills.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {savedRole.skills.map((skill) => (
                  <span
                    key={skill.skill_name}
                    className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-800"
                  >
                    {skill.skill_name}
                    <span className="text-indigo-500">· {skill.required_proficiency}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-sm text-gray-500">No skills specified.</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Post-save success state
  if (flowState === "success" && savedRole) {
    return (
      <div className="space-y-6">
        <div
          className="rounded-lg border border-green-200 bg-green-50 p-6 text-center"
          role="status"
          aria-live="polite"
        >
          <h2 className="text-xl font-semibold text-green-800">Target Role Set Successfully!</h2>
          <p className="mt-2 text-green-700">
            Your target role has been set to <strong>{savedRole.role_title}</strong> with{" "}
            {savedRole.skills.length} required skill{savedRole.skills.length !== 1 ? "s" : ""}.
          </p>
          <p className="mt-1 text-sm text-green-600">
            You can now proceed to run a skill gap analysis.
          </p>
          <button
            type="button"
            onClick={() => setFlowState("saved")}
            className="mt-4 rounded-md border border-green-300 px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            View Role Details
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link when changing an existing role */}
      {targetRole && (
        <button
          type="button"
          onClick={() => setFlowState("saved")}
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
        >
          ← Back to current role
        </button>
      )}

      <section aria-labelledby="target-role-heading">
        <h2 id="target-role-heading" className="mb-4 text-xl font-semibold text-gray-800">
          {targetRole ? "Change Target Role" : "Select Your Target Role"}
        </h2>
        <p className="mb-6 text-sm text-gray-600">
          Enter the role you want to transition to. We&apos;ll identify the skills and
          competencies required so we can analyze your gaps.
        </p>

        {/* Role Title Input */}
        {(flowState === "input" || flowState === "loading") && (
          <form onSubmit={handleSearchRole} className="space-y-4">
            <div>
              <label
                htmlFor="role-title"
                className="block text-sm font-medium text-gray-700"
              >
                Target Role Title
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  id="role-title"
                  type="text"
                  value={roleTitle}
                  onChange={(e) => {
                    setRoleTitle(e.target.value);
                    if (roleTitleError) setRoleTitleError(null);
                  }}
                  placeholder="e.g., Senior Software Engineer, Data Scientist, Product Manager"
                  disabled={flowState === "loading"}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-500"
                  aria-describedby={roleTitleError ? "role-title-error" : "role-title-hint"}
                  aria-invalid={!!roleTitleError}
                />
                <button
                  type="submit"
                  disabled={flowState === "loading"}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
                >
                  {flowState === "loading" ? (
                    <span className="flex items-center gap-2">
                      <svg
                        className="h-4 w-4 animate-spin"
                        fill="none"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Searching...
                    </span>
                  ) : (
                    "Find Role"
                  )}
                </button>
              </div>
              {roleTitleError && (
                <p id="role-title-error" className="mt-1 text-sm text-red-600" role="alert">
                  {roleTitleError}
                </p>
              )}
              {!roleTitleError && (
                <p id="role-title-hint" className="mt-1 text-xs text-gray-500">
                  Enter a role title between 1 and 100 characters.
                </p>
              )}
            </div>
          </form>
        )}

        {/* Recognized Role - Show Skills */}
        {flowState === "recognized" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 p-3">
              <div>
                <p className="text-sm font-medium text-green-800">
                  Role recognized: <strong>{roleTitle}</strong>
                </p>
                <p className="text-xs text-green-600">
                  Review and customize the required skills below.
                </p>
              </div>
              <button
                type="button"
                onClick={handleReset}
                className="text-sm text-green-700 underline hover:text-green-900"
              >
                Change role
              </button>
            </div>

            <SkillRequirementsList skills={skills} onSkillsChange={setSkills} />

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleSaveRecognizedRole}
                disabled={isSubmitting || skills.length === 0}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isSubmitting ? "Saving..." : "Confirm Target Role"}
              </button>
              <button
                type="button"
                onClick={handleReset}
                disabled={isSubmitting}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Unrecognized Role - Custom Form */}
        {flowState === "unrecognized" && (
          <CustomRoleForm
            roleTitle={roleTitle.trim()}
            onSubmit={handleSaveCustomRole}
            onCancel={handleReset}
            isSubmitting={isSubmitting}
          />
        )}
      </section>

      {/* API Error Display */}
      {apiError && (
        <div
          className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          role="alert"
        >
          {apiError}
        </div>
      )}
    </div>
  );
}
