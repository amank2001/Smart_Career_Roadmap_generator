"use client";

import { useState } from "react";
import type { SkillRequirement, ProficiencyLevel, GapCategory } from "@/types/target-role";

interface SkillRequirementItemProps {
  skill: SkillRequirement;
  index: number;
  onUpdate: (index: number, updated: SkillRequirement) => void;
  onRemove: (index: number) => void;
}

const PROFICIENCY_OPTIONS: { value: ProficiencyLevel; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const CATEGORY_OPTIONS: { value: GapCategory; label: string }[] = [
  { value: "critical", label: "Critical" },
  { value: "important", label: "Important" },
  { value: "nice-to-have", label: "Nice to have" },
];

export function SkillRequirementItem({
  skill,
  index,
  onUpdate,
  onRemove,
}: SkillRequirementItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(skill.skill_name);
  const [editProficiency, setEditProficiency] = useState(skill.required_proficiency);
  const [editCategory, setEditCategory] = useState(skill.category);

  function handleSave() {
    if (!editName.trim()) return;
    onUpdate(index, {
      skill_name: editName.trim(),
      required_proficiency: editProficiency,
      category: editCategory,
    });
    setIsEditing(false);
  }

  function handleCancel() {
    setEditName(skill.skill_name);
    setEditProficiency(skill.required_proficiency);
    setEditCategory(skill.category);
    setIsEditing(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  }

  const categoryColors: Record<GapCategory, string> = {
    critical: "bg-red-100 text-red-800 border-red-200",
    important: "bg-yellow-100 text-yellow-800 border-yellow-200",
    "nice-to-have": "bg-blue-100 text-blue-800 border-blue-200",
  };

  if (isEditing) {
    return (
      <li className="flex flex-col gap-2 rounded-md border border-indigo-200 bg-indigo-50 p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label htmlFor={`skill-name-${index}`} className="sr-only">
            Skill name
          </label>
          <input
            id={`skill-name-${index}`}
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            aria-label={`Edit skill name for skill ${index + 1}`}
            autoFocus
          />
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label htmlFor={`skill-proficiency-${index}`} className="text-xs text-gray-600">
            Proficiency:
          </label>
          <select
            id={`skill-proficiency-${index}`}
            value={editProficiency}
            onChange={(e) => setEditProficiency(e.target.value as ProficiencyLevel)}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {PROFICIENCY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <label htmlFor={`skill-category-${index}`} className="text-xs text-gray-600">
            Category:
          </label>
          <select
            id={`skill-category-${index}`}
            value={editCategory}
            onChange={(e) => setEditCategory(e.target.value as GapCategory)}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={!editName.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Save
          </button>
          <button
            type="button"
            onClick={handleCancel}
            className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </li>
    );
  }

  return (
    <li className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-gray-900">{skill.skill_name}</span>
        <span
          className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${categoryColors[skill.category]}`}
        >
          {skill.category}
        </span>
        <span className="text-xs text-gray-500">{skill.required_proficiency}</span>
      </div>
      <div className="flex gap-1">
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          aria-label={`Edit ${skill.skill_name}`}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={() => onRemove(index)}
          className="rounded-md p-1.5 text-red-500 hover:bg-red-50 hover:text-red-700"
          aria-label={`Remove ${skill.skill_name}`}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </li>
  );
}
