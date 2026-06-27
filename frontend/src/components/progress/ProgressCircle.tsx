"use client";

interface ProgressCircleProps {
  /** Progress percentage (0–100) */
  percentage: number;
  /** Optional size in pixels (default: 160) */
  size?: number;
}

/**
 * A circular progress indicator displaying the overall completion percentage.
 * Requirement 8.1: Display overall progress as integer 0-100.
 */
export function ProgressCircle({ percentage, size = 160 }: ProgressCircleProps) {
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center"
      role="meter"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Overall progress: ${percentage}%`}
    >
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
        aria-hidden="true"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-200"
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="text-indigo-600 transition-all duration-500 ease-in-out"
        />
      </svg>
      <div className="mt-3 text-center">
        <span className="text-3xl font-bold text-gray-900">{`${percentage}%`}</span>
        <p className="text-sm text-gray-500">Complete</p>
      </div>
    </div>
  );
}
