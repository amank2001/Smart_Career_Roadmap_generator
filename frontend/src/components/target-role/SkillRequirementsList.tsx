"use client";

import { useState } from "react";
import type { SkillRequirement, ProficiencyLevel, GapCategory } from "@/types/target-role";
import { SkillRequirementItem } from "./SkillRequirementItem";

interface SkillRequirementsListProps {
  skills: SkillRequirement[];
  onSkillsChange: (skills: SkillRequirement[]) => void;
  minSkills?: number;
}

const DEFAULT_PROFICIENCY: ProficiencyLevel = "intermediate";
const DEFAULT_CATEGORY: GapCategory = "important";

export function SkillRequirementsList({
  skills,
  onSkillsChange,
  minSkills = 0,
}: SkillRequirementsListProps) {
  const [newSkillName, setNewSkillName] = useState("");
  const [newProficiency, setNewProficiency] = useState<ProficiencyLevel>(DEFAULT_PROFICIENCY);
  const [newCategory, setNewCategory] = useState<GapCategory>(DEFAULT_CATEGORY);
  const [addError, setAddError] = useState<string | null>(null);

  function handleAddSkill() {
    const trimmed = newSkillName.trim();
    if (!trimmed) {
      setAddError("Skill name cannot be empty");
      return;
    }
    if (trimmed.length > 60) {
      setAddError("Skill name must be 60 characters or fewer");
      return;
    }
    if (skills.some((s) => s.skill_name.toLowerCase() === trimmed.toLowerCase())) {
      setAddError("This skill has already been added");
      return;
    }

    const newSkill: SkillRequirement = {
      skill_name: trimmed,
      required_proficiency: newProficiency,
      category: newCategory,
    };

    onSkillsChange([...skills, newSkill]);
    setNewSkillName("");
    setNewProficiency(DEFAULT_PROFICIENCY);
    setNewCategory(DEFAULT_CATEGORY);
    setAddError(null);
  }

  function handleUpdate(index: number, updated: SkillRequirement) {
    const updatedSkills = [...skills];
    updatedSkills[index] = updated;
    onSkillsChange(updatedSkills);
  }

  function handleRemove(index: number) {
    if (skills.length <= minSkills) return;
    const updatedSkills = skills.filter((_, i) => i !== index);
    onSkillsChange(updatedSkills);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddSkill();
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700">
          Skills & Competencies ({skills.length})
        </h3>
        {minSkills > 0 && skills.length < minSkills && (
          <span className="text-xs text-red-600" role="alert">
            At least {minSkills} skills required
          </span>
        )}
      </div>

      {skills.length > 0 && (
        <ul className="space-y-2" aria-label="Required skills list">
          {skills.map((skill, index) => (
            <SkillRequirementItem
              key={`${skill.skill_name}-${index}`}
              skill={skill}
              index={index}
              onUpdate={handleUpdate}
              onRemove={handleRemove}
            />
          ))}
        </ul>
      )}

      {skills.length === 0 && (
        <p className="rounded-md border border-dashed border-gray-300 p-4 text-center text-sm text-gray-500">
          No skills added yet. Add skills below.
        </p>
      )}

      <fieldset className="rounded-md border border-gray-200 p-3">
        <legend className="px-1 text-xs font-medium text-gray-600">Add a skill</legend>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="new-skill-name" className="sr-only">
              Skill name
            </label>
            <input
              id="new-skill-name"
              type="text"
              value={newSkillName}
              onChange={(e) => {
                setNewSkillName(e.target.value);
                if (addError) setAddError(null);
              }}
              onKeyDown={handleKeyDown}
              placeholder="e.g., React, System Design, Leadership"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              aria-describedby={addError ? "add-skill-error" : undefined}
              aria-invalid={!!addError}
            />
          </div>
          <div>
            <label htmlFor="new-skill-proficiency" className="sr-only">
              Required proficiency
            </label>
            <select
              id="new-skill-proficiency"
              value={newProficiency}
              onChange={(e) => setNewProficiency(e.target.value as ProficiencyLevel)}
              className="rounded-md border border-gray-300 px-2 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
          <div>
            <label htmlFor="new-skill-category" className="sr-only">
              Category
            </label>
            <select
              id="new-skill-category"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value as GapCategory)}
              className="rounded-md border border-gray-300 px-2 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="critical">Critical</option>
              <option value="important">Important</option>
              <option value="nice-to-have">Nice to have</option>
            </select>
          </div>
          <button
            type="button"
            onClick={handleAddSkill}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Add
          </button>
        </div>
        {addError && (
          <p id="add-skill-error" className="mt-1 text-xs text-red-600" role="alert">
            {addError}
          </p>
        )}
      </fieldset>
    </div>
  );
}
