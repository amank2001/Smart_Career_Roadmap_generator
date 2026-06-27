"use client";

import { useState } from "react";
import type { CreateProfileInput, Skill } from "@/lib/api";

interface ProfileFormProps {
  onSubmit: (data: CreateProfileInput) => Promise<void>;
  isSubmitting: boolean;
  initialData?: {
    currentJobTitle: string;
    yearsOfExperience: number;
    skills: string[];
  };
}

export function ProfileForm({ onSubmit, isSubmitting, initialData }: ProfileFormProps) {
  const [jobTitle, setJobTitle] = useState(initialData?.currentJobTitle ?? "");
  const [yearsOfExperience, setYearsOfExperience] = useState(
    initialData?.yearsOfExperience?.toString() ?? ""
  );
  const [skills, setSkills] = useState<string[]>(initialData?.skills ?? []);
  const [skillInput, setSkillInput] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  function addSkill() {
    const trimmed = skillInput.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setSkillInput("");
      setErrors((prev) => ({ ...prev, skills: "" }));
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

  function validate(): boolean {
    const newErrors: Record<string, string> = {};

    if (!jobTitle.trim()) {
      newErrors.jobTitle = "Job title is required.";
    }

    const years = parseInt(yearsOfExperience, 10);
    if (isNaN(years) || years < 0) {
      newErrors.yearsOfExperience = "Please enter a valid number of years.";
    }

    if (skills.length === 0) {
      newErrors.skills = "Please add at least one skill.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const skillObjects: Skill[] = skills.map((name) => ({
      name,
      proficiency_level: null,
    }));

    await onSubmit({
      current_job_title: jobTitle.trim(),
      years_of_experience: parseInt(yearsOfExperience, 10),
      skills: skillObjects,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="job-title" className="block text-sm font-medium text-gray-700">
          Current Job Title
        </label>
        <input
          id="job-title"
          type="text"
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="e.g. Software Engineer"
          disabled={isSubmitting}
        />
        {errors.jobTitle && (
          <p className="mt-1 text-xs text-red-600" role="alert">{errors.jobTitle}</p>
        )}
      </div>

      <div>
        <label htmlFor="years-experience" className="block text-sm font-medium text-gray-700">
          Years of Experience
        </label>
        <input
          id="years-experience"
          type="number"
          min="0"
          max="50"
          value={yearsOfExperience}
          onChange={(e) => setYearsOfExperience(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="e.g. 3"
          disabled={isSubmitting}
        />
        {errors.yearsOfExperience && (
          <p className="mt-1 text-xs text-red-600" role="alert">{errors.yearsOfExperience}</p>
        )}
      </div>

      <div>
        <label htmlFor="skill-input" className="block text-sm font-medium text-gray-700">
          Skills
        </label>
        <div className="mt-1 flex gap-2">
          <input
            id="skill-input"
            type="text"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={handleSkillKeyDown}
            className="block flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Type a skill and press Enter"
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
        {errors.skills && (
          <p className="mt-1 text-xs text-red-600" role="alert">{errors.skills}</p>
        )}
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

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? "Creating Profile..." : "Create Profile"}
      </button>
    </form>
  );
}
