"use client";

import { ProjectSuggestions } from "@/components/projects/ProjectSuggestions";

/**
 * Projects page – shows AI-generated project suggestions.
 * Uses GET /api/projects/suggestions which automatically picks the best
 * weekly plan (in-progress → upcoming → completed) from the user's roadmap.
 */
export default function ProjectsPage() {
  return (
    <div>
      <ProjectSuggestions />
    </div>
  );
}
