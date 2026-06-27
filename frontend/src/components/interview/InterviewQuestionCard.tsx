"use client";

import type { InterviewQuestion, InterviewCategory, DifficultyLevel } from "@/types/interview";

const CATEGORY_STYLES: Record<InterviewCategory, string> = {
  technical: "bg-purple-100 text-purple-800",
  behavioral: "bg-green-100 text-green-800",
  "system-design": "bg-orange-100 text-orange-800",
};

const CATEGORY_LABELS: Record<InterviewCategory, string> = {
  technical: "Technical",
  behavioral: "Behavioral",
  "system-design": "System Design",
};

const DIFFICULTY_STYLES: Record<DifficultyLevel, string> = {
  beginner: "bg-emerald-100 text-emerald-800",
  intermediate: "bg-amber-100 text-amber-800",
  advanced: "bg-red-100 text-red-800",
};

const DIFFICULTY_LABELS: Record<DifficultyLevel, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

interface InterviewQuestionCardProps {
  question: InterviewQuestion;
  questionNumber: number;
  isActive: boolean;
  onSelect: (questionId: string) => void;
}

export function InterviewQuestionCard({
  question,
  questionNumber,
  isActive,
  onSelect,
}: InterviewQuestionCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(question.id)}
      className={`w-full rounded-lg border p-4 text-left transition-colors ${
        isActive
          ? "border-indigo-300 bg-indigo-50 ring-2 ring-indigo-200"
          : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
      }`}
      aria-pressed={isActive}
      aria-label={`Question ${questionNumber}: ${question.question}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-gray-500">
          Q{questionNumber}
        </span>
        <div className="flex gap-1.5">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_STYLES[question.category]}`}
          >
            {CATEGORY_LABELS[question.category]}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${DIFFICULTY_STYLES[question.difficulty]}`}
          >
            {DIFFICULTY_LABELS[question.difficulty]}
          </span>
        </div>
      </div>
      <p className="mt-2 text-sm text-gray-800 line-clamp-2">
        {question.question}
      </p>
    </button>
  );
}
