"use client";

import { useState } from "react";
import type { CreateProfileInput, Skill } from "@/lib/api";

interface ExtractedData {
  skills?: string[];
  job_history?: string[];
  years_of_experience?: number;
  current_job_title?: string;
}

interface ResumeDataConfirmationProps {
  extractedData: ExtractedData;
  onConfirm: (data: CreateProfileInput) => Promise<void>;
  onBack: () => void;
  isSubmitting: boolean;
}

export function ResumeDataConfirmation({
  extractedData,
  onConfirm,
  onBack,
  isSubmitting,
}: ResumeDataConfirmationProps) {
  const [jobTitle, setJobTitle] = useState(extractedData.current_job_title ?? "");
  const [yearsOfExperience, setYearsOfExperience] = useState(
    extractedData.years_of_experience?.toString() ?? "0"
  );
  const [skills, setSkills] = useState<string[]>(extractedData.skills ?? []);
  const [skillInput, setSkillInput] = useState("");

  function addSkill() {
    const trimmed = skillInput.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setSkillInput("");
    }
  }

  function removeSkill(skillToRemove: string) {
    setSkills(skills.filter((s) => s !== skillToRemove));
  }

  function handleSkillKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      addSkill();
    }
  }

  async function handleConfirm() {
    const skillObjects: Skill[] = skills.map((name) => ({
      name,
      proficiency_level: null,
    }));

    await onConfirm({
      current_job_title: jobTitle.trim(),
      years_of_experience: parseInt(yearsOfExperience, 10) || 0,
      skills: skillObjects,
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Confirm Extracted Data</h2>
        <p className="mt-1 text-sm text-gray-600">
          We extracted the following information from your resume. Please review and edit if needed.
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
        <div>
          <label htmlFor="confirm-job-title" className="block text-sm font-medium text-gray-700">
            Job Title
          </label>
          <input
            id="confirm-job-title"
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            disabled={isSubmitting}
          />
        </div>

        <div>
          <label htmlFor="confirm-years" className="block text-sm font-medium text-gray-700">
            Years of Experience
          </label>
          <input
            id="confirm-years"
            type="number"
            min="0"
            max="50"
            value={yearsOfExperience}
            onChange={(e) => setYearsOfExperience(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            disabled={isSubmitting}
          />
        </div>

        <div>
          <label htmlFor="confirm-skill-input" className="block text-sm font-medium text-gray-700">
            Skills
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id="confirm-skill-input"
              type="text"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={handleSkillKeyDown}
              className="block flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="Add a skill"
              disabled={isSubmitting}
            />
            <button
              type="button"
              onClick={addSkill}
              disabled={isSubmitting || !skillInput.trim()}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50"
            >
              Add
            </button>
          </div>
          {skills.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-800"
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => removeSkill(skill)}
                    className="ml-0.5 text-indigo-600 hover:text-indigo-900"
                    aria-label={`Remove ${skill}`}
                    disabled={isSubmitting}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {extractedData.job_history && extractedData.job_history.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700">Job History (detected)</h3>
            <ul className="mt-1 space-y-1">
              {extractedData.job_history.map((job, i) => (
                <li key={i} className="text-sm text-gray-600">
                  {job}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          disabled={isSubmitting}
          className="rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
        >
          Back to Form
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isSubmitting}
          className="flex-1 rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Confirm & Create Profile"}
        </button>
      </div>
    </div>
  );
}
