"use client";

import { useState, useCallback } from "react";
import type { ResumeAnalysisResult } from "@/lib/api";
import { uploadResume, ApiError } from "@/lib/api";

interface ResumeUploadProps {
  onExtracted: (result: ResumeAnalysisResult) => void;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
];
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

export function ResumeUpload({ onExtracted }: ResumeUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);

      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError("Please upload a PDF or Word document (.pdf, .doc, .docx).");
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        setError("File size must be less than 5MB.");
        return;
      }

      setIsUploading(true);
      setProgress(0);

      try {
        const result = await uploadResume(file, setProgress);
        if (result.success) {
          onExtracted(result);
        } else {
          setError(result.error ?? "Failed to analyze resume.");
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.userMessage);
        } else {
          setError("An unexpected error occurred. Please try again.");
        }
      } finally {
        setIsUploading(false);
      }
    },
    [onExtracted]
  );

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  return (
    <div className="space-y-3">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          isDragOver
            ? "border-indigo-400 bg-indigo-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        }`}
      >
        <svg
          className="mb-3 h-10 w-10 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>

        {isUploading ? (
          <div className="text-center">
            <p className="text-sm text-gray-600">Uploading and analyzing...</p>
            <div className="mt-2 h-2 w-48 overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full rounded-full bg-indigo-600 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-500">{progress}%</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-600">
              Drag and drop your resume here, or{" "}
              <label
                htmlFor="resume-file-input"
                className="cursor-pointer font-medium text-indigo-600 hover:text-indigo-500"
              >
                browse
              </label>
            </p>
            <p className="mt-1 text-xs text-gray-500">PDF or Word document, max 5MB</p>
          </>
        )}

        <input
          id="resume-file-input"
          type="file"
          accept=".pdf,.doc,.docx"
          onChange={handleFileInput}
          disabled={isUploading}
          className="sr-only"
          aria-label="Upload resume file"
        />
      </div>

      {error && (
        <div
          className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </div>
      )}
    </div>
  );
}
