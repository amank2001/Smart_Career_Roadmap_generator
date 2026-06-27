"use client";

import { useState, useCallback } from "react";
import type { InterviewSession, InterviewQuestion } from "@/types/interview";
import { generateInterviewQuestions, InterviewApiError } from "@/lib/api/interview";
import { InterviewQuestionCard } from "./InterviewQuestionCard";
import { AnswerForm } from "./AnswerForm";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; session: InterviewSession; activeQuestionId: string | null };

export function InterviewPrep() {
  const [viewState, setViewState] = useState<ViewState>({ status: "idle" });

  const handleGenerate = useCallback(async () => {
    setViewState({ status: "loading" });
    try {
      const session = await generateInterviewQuestions();
      setViewState({
        status: "success",
        session,
        activeQuestionId: session.questions.length > 0 ? session.questions[0].id : null,
      });
    } catch (err) {
      if (err instanceof InterviewApiError) {
        setViewState({ status: "error", message: err.message });
      } else {
        setViewState({
          status: "error",
          message: "An unexpected error occurred while generating questions.",
        });
      }
    }
  }, []);

  function handleSelectQuestion(questionId: string) {
    if (viewState.status === "success") {
      setViewState({ ...viewState, activeQuestionId: questionId });
    }
  }

  const activeQuestion: InterviewQuestion | undefined =
    viewState.status === "success"
      ? viewState.session.questions.find((q) => q.id === viewState.activeQuestionId)
      : undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">
          Interview Preparation
        </h2>
        <button
          onClick={handleGenerate}
          disabled={viewState.status === "loading"}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Generate mock interview questions"
        >
          {viewState.status === "loading" ? "Generating..." : "Generate Questions"}
        </button>
      </div>

      {viewState.status === "idle" && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-sm text-gray-600">
            Click &quot;Generate Questions&quot; to create a mock interview session
            tailored to your target role and learning progress.
          </p>
        </div>
      )}

      {viewState.status === "loading" && (
        <div
          className="flex items-center justify-center py-12"
          role="status"
          aria-live="polite"
        >
          <div className="text-center">
            <div
              className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
              aria-hidden="true"
            />
            <p className="mt-3 text-sm text-gray-600">
              Generating interview questions...
            </p>
          </div>
        </div>
      )}

      {viewState.status === "error" && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h3 className="text-lg font-semibold text-red-800">
            Failed to Generate Questions
          </h3>
          <p className="mt-2 text-sm text-red-700">{viewState.message}</p>
          <button
            onClick={handleGenerate}
            className="mt-4 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Try Again
          </button>
        </div>
      )}

      {viewState.status === "success" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <aside
            className="space-y-2 lg:col-span-1"
            aria-label="Interview questions list"
          >
            <h3 className="text-sm font-medium text-gray-600">
              Questions ({viewState.session.questions.length})
            </h3>
            <div className="space-y-2 overflow-y-auto max-h-[600px]">
              {viewState.session.questions.map((question, index) => (
                <InterviewQuestionCard
                  key={question.id}
                  question={question}
                  questionNumber={index + 1}
                  isActive={question.id === viewState.activeQuestionId}
                  onSelect={handleSelectQuestion}
                />
              ))}
            </div>
          </aside>

          <main className="lg:col-span-2" aria-label="Active question and answer">
            {activeQuestion ? (
              <AnswerForm key={activeQuestion.id} question={activeQuestion} />
            ) : (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
                <p className="text-sm text-gray-600">
                  Select a question from the list to begin.
                </p>
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
