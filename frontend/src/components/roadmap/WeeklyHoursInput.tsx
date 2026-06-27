"use client";

import { useState, useCallback } from "react";

interface WeeklyHoursInputProps {
  currentHours: number;
  onHoursChange: (hours: number) => void;
  isUpdating: boolean;
}

const MIN_HOURS = 1;
const MAX_HOURS = 40;

export function WeeklyHoursInput({
  currentHours,
  onHoursChange,
  isUpdating,
}: WeeklyHoursInputProps) {
  const [inputValue, setInputValue] = useState(String(currentHours));
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(() => {
    const num = parseInt(inputValue, 10);
    if (isNaN(num) || num < MIN_HOURS || num > MAX_HOURS) {
      setError("Weekly study hours must be between 1 and 40");
      return;
    }
    setError(null);
    if (num !== currentHours) {
      onHoursChange(num);
    }
  }, [inputValue, currentHours, onHoursChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleBlur = useCallback(() => {
    handleSubmit();
  }, [handleSubmit]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value);
      setError(null);
    },
    []
  );

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor="weekly-hours-input"
        className="text-sm font-medium text-gray-700"
      >
        Weekly study hours
      </label>
      <div className="flex items-center gap-2">
        <input
          id="weekly-hours-input"
          type="number"
          min={MIN_HOURS}
          max={MAX_HOURS}
          value={inputValue}
          onChange={handleChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          disabled={isUpdating}
          aria-describedby={error ? "weekly-hours-error" : undefined}
          aria-invalid={error ? "true" : "false"}
          className="w-20 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <span className="text-sm text-gray-500">hrs/week (1-40)</span>
        {isUpdating && (
          <span className="text-xs text-indigo-600" aria-live="polite">
            Recalculating...
          </span>
        )}
      </div>
      {error && (
        <p
          id="weekly-hours-error"
          className="text-xs text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}
