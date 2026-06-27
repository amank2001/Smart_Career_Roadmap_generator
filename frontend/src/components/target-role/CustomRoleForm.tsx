"use client";

import { useState } from "react";
import type { SkillRequirement } from "@/types/target-role";
import { SkillRequirementsList } from "./SkillRequirementsList";
import {
  validateCustomRoleSkillCount,
  validateResponsibilities,
  CONSTRAINTS,
} from "@/lib/validation";

interface CustomRoleFormProps {
  roleTitle: string;
  onSubmit: (skills: SkillRequirement[], responsibilities: string) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

export function CustomRoleForm({
  roleTitle,
  onSubmit,
  onCancel,
  isSubmitting,
}: CustomRoleFormProps) {
  const [skills, setSkills] = useState<SkillRequirement[]>([]);
  const [responsibilities, setResponsibilities] = useState("");
  const [errors, setErrors] = useState<{ skills?: string; responsibilities?: string }>({});

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const newErrors: { skills?: string; responsibilities?: string } = {};

    const skillErr = validateCustomRoleSkillCount(skills.length);
    if (skillErr) newErrors.skills = skillErr;

    const respErr = validateResponsibilities(responsibilities);
    if (respErr) newErrors.responsibilities = respErr;

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    onSubmit(skills, responsibilities.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" aria-labelledby="custom-role-heading">
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
        <div className="flex">
          <svg
            className="h-5 w-5 text-amber-500"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd"
            />
          </svg>
          <div className="ml-3">
            <h3 id="custom-role-heading" className="text-sm font-medium text-amber-800">
              Unrecognized Role: &ldquo;{roleTitle}&rdquo;
            </h3>
            <p className="mt-1 text-sm text-amber-700">
              This role isn&apos;t in our database. Please provide at least{" "}
              {CONSTRAINTS.CUSTOM_ROLE_SKILLS_MIN} skills and a description of the role&apos;s
              responsibilities so we can create custom requirements.
            </p>
          </div>
        </div>
      </div>

      <div>
        <SkillRequirementsList
          skills={skills}
          onSkillsChange={(updated) => {
            setSkills(updated);
            if (errors.skills) setErrors((prev) => ({ ...prev, skills: undefined }));
          }}
          minSkills={CONSTRAINTS.CUSTOM_ROLE_SKILLS_MIN}
        />
        {errors.skills && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.skills}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="responsibilities"
          className="block text-sm font-medium text-gray-700"
        >
          Role Responsibilities
        </label>
        <textarea
          id="responsibilities"
          value={responsibilities}
          onChange={(e) => {
            setResponsibilities(e.target.value);
            if (errors.responsibilities)
              setErrors((prev) => ({ ...prev, responsibilities: undefined }));
          }}
          rows={4}
          placeholder="Describe the key responsibilities of this role..."
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          aria-describedby={errors.responsibilities ? "responsibilities-error" : undefined}
          aria-invalid={!!errors.responsibilities}
        />
        {errors.responsibilities && (
          <p id="responsibilities-error" className="mt-1 text-sm text-red-600" role="alert">
            {errors.responsibilities}
          </p>
        )}
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Save Custom Role"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
