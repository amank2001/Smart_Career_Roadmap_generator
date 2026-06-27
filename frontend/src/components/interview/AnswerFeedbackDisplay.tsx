"use client";

import type { AnswerFeedback } from "@/types/interview";

interface AnswerFeedbackDisplayProps {
  feedback: AnswerFeedback;
}

export function AnswerFeedbackDisplay({ feedback }: AnswerFeedbackDisplayProps) {
  return (
    <div className="space-y-4" aria-label="Answer feedback">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="text-sm font-semibold text-gray-800">
          Overall Assessment
        </h4>
        <p className="mt-1 text-sm text-gray-700">
          {feedback.overall_assessment}
        </p>
      </div>

      {feedback.strengths.length > 0 && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <h4 className="text-sm font-semibold text-green-800">Strengths</h4>
          <ul className="mt-2 space-y-1" aria-label="Answer strengths">
            {feedback.strengths.map((strength, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-green-700">
                <span aria-hidden="true" className="mt-0.5 text-green-500">
                  &#10003;
                </span>
                {strength}
              </li>
            ))}
          </ul>
        </div>
      )}

      {feedback.areas_for_improvement.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h4 className="text-sm font-semibold text-amber-800">
            Areas for Improvement
          </h4>
          <ul className="mt-2 space-y-1" aria-label="Areas for improvement">
            {feedback.areas_for_improvement.map((area, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                <span aria-hidden="true" className="mt-0.5 text-amber-500">
                  &#9679;
                </span>
                {area}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
