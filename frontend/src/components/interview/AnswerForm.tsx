"use client";

import { useState } from "react";
import type { InterviewQuestion, AnswerFeedback } from "@/types/interview";
import { submitAnswer, InterviewApiError } from "@/lib/api/interview";
import { AnswerFeedbackDisplay } from "./AnswerFeedbackDisplay";

interface AnswerFormProps {
  question: InterviewQuestion;
}

export function AnswerForm({ question }: AnswerFormProps) {
  const [answer, setAnswer] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<AnswerFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showModelAnswer, setShowModelAnswer] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!answer.trim()) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const result = await submitAnswer(question.id, answer.trim());
      setFeedback(result);
    } catch (err) {
      if (err instanceof InterviewApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setAnswer("");
    setFeedback(null);
    setError(null);
    setShowModelAnswer(false);
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h3 className="text-lg font-medium text-gray-900">
          {question.question}
        </h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="text-xs text-gray-500">
            Evaluation criteria:
          </span>
          {question.evaluation_criteria.map((criterion, i) => (
            <span
              key={i}
              className="inline-flex rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
            >
              {criterion}
            </span>
          ))}
        </div>
      </div>

      {!feedback ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <label htmlFor="answer-input" className="block text-sm font-medium text-gray-700">
            Your Answer
          </label>
          <textarea
            id="answer-input"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={6}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Type your answer here..."
            disabled={isSubmitting}
            aria-describedby="answer-help"
          />
          <p id="answer-help" className="text-xs text-gray-500">
            Write your answer as you would in a real interview. The AI will evaluate it against the criteria above.
          </p>
          {error && (
            <div
              className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
              role="alert"
            >
              {error}
            </div>
          )}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isSubmitting || !answer.trim()}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? "Evaluating..." : "Submit Answer"}
            </button>
            <button
              type="button"
              onClick={() => setShowModelAnswer(!showModelAnswer)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              {showModelAnswer ? "Hide Model Answer" : "Show Model Answer"}
            </button>
          </div>
        </form>
      ) : (
        <div className="space-y-4">
          <AnswerFeedbackDisplay feedback={feedback} />
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleReset}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Try Again
            </button>
            <button
              type="button"
              onClick={() => setShowModelAnswer(!showModelAnswer)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              {showModelAnswer ? "Hide Model Answer" : "Show Model Answer"}
            </button>
          </div>
        </div>
      )}

      {showModelAnswer && (
        <div
          className="rounded-lg border border-blue-200 bg-blue-50 p-4"
          aria-label="Model answer"
        >
          <h4 className="text-sm font-medium text-blue-800">Model Answer</h4>
          <p className="mt-2 whitespace-pre-wrap text-sm text-blue-700">
            {question.model_answer}
          </p>
        </div>
      )}
    </div>
  );
}
