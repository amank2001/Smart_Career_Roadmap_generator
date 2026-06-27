"use client";

import type { RoadmapTopic, LearningResource } from "@/types/roadmap";

const CATEGORY_STYLES: Record<string, { badge: string }> = {
  critical: { badge: "bg-red-100 text-red-800" },
  important: { badge: "bg-yellow-100 text-yellow-800" },
  "nice-to-have": { badge: "bg-blue-100 text-blue-800" },
};

const CATEGORY_LABELS: Record<string, string> = {
  critical: "Critical",
  important: "Important",
  "nice-to-have": "Nice to Have",
};

const RESOURCE_TYPE_ICONS: Record<string, string> = {
  course: "\uD83C\uDF93",
  book: "\uD83D\uDCD6",
  tutorial: "\uD83D\uDCBB",
  documentation: "\uD83D\uDCC4",
};

function ResourceItem({ resource }: { resource: LearningResource }) {
  const icon = RESOURCE_TYPE_ICONS[resource.type] ?? "\uD83D\uDD17";

  return (
    <li className="flex items-start gap-2 text-sm text-gray-700">
      <span aria-hidden="true">{icon}</span>
      <div>
        {resource.url ? (
          <a
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 underline hover:text-indigo-800"
          >
            {resource.title}
          </a>
        ) : (
          <span>{resource.title}</span>
        )}
        <span className="ml-1 text-xs text-gray-500">{`(${resource.type})`}</span>
      </div>
    </li>
  );
}

interface RoadmapTopicCardProps {
  topic: RoadmapTopic;
  index: number;
}

export function RoadmapTopicCard({ topic, index }: RoadmapTopicCardProps) {
  const styles = CATEGORY_STYLES[topic.category] ?? { badge: "bg-gray-100 text-gray-800" };

  return (
    <article
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
      aria-label={`Topic ${index + 1}: ${topic.skill_name}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
            {index + 1}
          </span>
          <h4 className="text-sm font-medium text-gray-900">
            {topic.skill_name}
          </h4>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles.badge}`}
        >
          {CATEGORY_LABELS[topic.category] ?? topic.category}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
        <span>Target: {topic.proficiency_target}</span>
        <span>{topic.estimated_hours}h estimated</span>
      </div>

      {topic.resources.length > 0 && (
        <div className="mt-3">
          <h5 className="text-xs font-medium text-gray-600">Resources:</h5>
          <ul className="mt-1 space-y-1" aria-label={`Resources for ${topic.skill_name}`}>
            {topic.resources.map((resource, idx) => (
              <ResourceItem key={idx} resource={resource} />
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
