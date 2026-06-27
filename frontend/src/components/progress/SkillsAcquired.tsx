"use client";

interface SkillsAcquiredProps {
  skills: string[];
}

/**
 * Displays a list of skills acquired through completed weekly plans.
 * Requirement 8.2: Show skills acquired from completed plans.
 */
export function SkillsAcquired({ skills }: SkillsAcquiredProps) {
  if (skills.length === 0) {
    return (
      <p className="text-sm text-gray-500" role="status">
        No skills acquired yet. Complete weekly plans to see your skill progress here.
      </p>
    );
  }

  return (
    <div>
      <ul
        className="grid grid-cols-1 gap-2 sm:grid-cols-2"
        aria-label="Skills acquired"
      >
        {skills.map((skill) => (
          <li
            key={skill}
            className="flex items-center gap-2 rounded-md border border-green-100 bg-green-50 px-3 py-2 text-sm text-green-800"
          >
            <span aria-hidden="true" className="text-green-500">
              &#10003;
            </span>
            {skill}
          </li>
        ))}
      </ul>
    </div>
  );
}
