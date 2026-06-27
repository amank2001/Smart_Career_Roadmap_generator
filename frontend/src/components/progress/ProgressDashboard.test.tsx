import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { ProgressDashboard } from "./ProgressDashboard";
import { ProgressApiError } from "@/lib/api/progress";
import type { ProgressSummary, TimelineEntry } from "@/types/progress";

// Mock the API module
jest.mock("@/lib/api/progress", () => {
  const actual = jest.requireActual("@/lib/api/progress");
  return {
    ...actual,
    getProgressSummary: jest.fn(),
    getProgressTimeline: jest.fn(),
  };
});

import { getProgressSummary, getProgressTimeline } from "@/lib/api/progress";

const mockedGetSummary = getProgressSummary as jest.MockedFunction<typeof getProgressSummary>;
const mockedGetTimeline = getProgressTimeline as jest.MockedFunction<typeof getProgressTimeline>;

const mockSummary: ProgressSummary = {
  percentage: 40,
  completed_plans: 2,
  total_plans: 5,
  skills_acquired: ["React", "TypeScript"],
};

const mockTimeline: TimelineEntry[] = [
  { week_number: 1, plan_id: "plan-1", status: "completed", skills: ["React"] },
  { week_number: 2, plan_id: "plan-2", status: "completed", skills: ["TypeScript"] },
  { week_number: 3, plan_id: "plan-3", status: "in-progress", skills: ["Node.js"] },
  { week_number: 4, plan_id: "plan-4", status: "upcoming", skills: ["Docker"] },
  { week_number: 5, plan_id: "plan-5", status: "upcoming", skills: ["Kubernetes"] },
];

describe("ProgressDashboard", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("shows loading state on initial render", () => {
    mockedGetSummary.mockImplementation(() => new Promise(() => {}));
    mockedGetTimeline.mockImplementation(() => new Promise(() => {}));

    render(<ProgressDashboard />);

    expect(screen.getByText("Loading progress data...")).toBeInTheDocument();
  });

  it("displays progress percentage in a circular indicator", async () => {
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("40%")).toBeInTheDocument();
    });

    expect(screen.getByLabelText("Overall progress: 40%")).toBeInTheDocument();
  });

  it("displays completed and total plan counts", async () => {
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    expect(screen.getByText("Plans Completed")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Total Plans")).toBeInTheDocument();
  });

  it("displays remaining plans message", async () => {
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("40%")).toBeInTheDocument();
    });

    expect(screen.getByText("3 weekly plans remaining.")).toBeInTheDocument();
  });

  it("displays skills acquired", async () => {
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("40%")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Skills Acquired" })).toBeInTheDocument();
    const skillsList = screen.getByRole("list", { name: "Skills acquired" });
    expect(skillsList).toBeInTheDocument();
    expect(skillsList.querySelectorAll("li")).toHaveLength(2);
  });

  it("displays timeline with status indicators", async () => {
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Week 1")).toBeInTheDocument();
    });

    expect(screen.getByText("Week 2")).toBeInTheDocument();
    expect(screen.getByText("Week 3")).toBeInTheDocument();
    expect(screen.getByText("Week 4")).toBeInTheDocument();
    expect(screen.getByText("Week 5")).toBeInTheDocument();

    // Check status labels
    const completedBadges = screen.getAllByText("Completed");
    expect(completedBadges).toHaveLength(2);
    expect(screen.getByText("In Progress")).toBeInTheDocument();
    const upcomingBadges = screen.getAllByText("Upcoming");
    expect(upcomingBadges).toHaveLength(2);
  });

  it("shows milestone notifications for fully achieved skills", async () => {
    // React and TypeScript are only in completed plans, so they are milestone-achieved
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByLabelText("Dismiss React milestone notification")).toBeInTheDocument();
    });

    expect(screen.getByLabelText("Dismiss TypeScript milestone notification")).toBeInTheDocument();
  });

  it("does not show milestone notification for skills still in progress", async () => {
    // Node.js is in-progress, Docker and Kubernetes are upcoming
    mockedGetSummary.mockResolvedValue(mockSummary);
    mockedGetTimeline.mockResolvedValue(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("40%")).toBeInTheDocument();
    });

    expect(screen.queryByText(/Milestone achieved:.*Node\.js/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Milestone achieved:.*Docker/)).not.toBeInTheDocument();
  });

  it("shows error state with retry button", async () => {
    mockedGetSummary.mockRejectedValue(
      new ProgressApiError("ROADMAP_NOT_FOUND", "No roadmap found")
    );
    mockedGetTimeline.mockRejectedValue(
      new ProgressApiError("ROADMAP_NOT_FOUND", "No roadmap found")
    );

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Unable to Load Progress")).toBeInTheDocument();
    });

    expect(screen.getByText("No roadmap found")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("retries data fetch when Try Again is clicked", async () => {
    mockedGetSummary
      .mockRejectedValueOnce(new ProgressApiError("UNKNOWN", "Network error"))
      .mockResolvedValueOnce(mockSummary);
    mockedGetTimeline
      .mockRejectedValueOnce(new ProgressApiError("UNKNOWN", "Network error"))
      .mockResolvedValueOnce(mockTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Unable to Load Progress")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Try Again"));

    await waitFor(() => {
      expect(screen.getByText("40%")).toBeInTheDocument();
    });
  });

  it("shows completion message when roadmap is 100% done", async () => {
    const completedSummary: ProgressSummary = {
      percentage: 100,
      completed_plans: 5,
      total_plans: 5,
      skills_acquired: ["React", "TypeScript", "Node.js", "Docker", "Kubernetes"],
    };
    const completedTimeline: TimelineEntry[] = mockTimeline.map((e) => ({
      ...e,
      status: "completed" as const,
    }));

    mockedGetSummary.mockResolvedValue(completedSummary);
    mockedGetTimeline.mockResolvedValue(completedTimeline);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Congratulations! You have completed your learning roadmap.")
    ).toBeInTheDocument();
  });

  it("shows empty state when no roadmap exists", async () => {
    const emptySummary: ProgressSummary = {
      percentage: 0,
      completed_plans: 0,
      total_plans: 0,
      skills_acquired: [],
    };

    mockedGetSummary.mockResolvedValue(emptySummary);
    mockedGetTimeline.mockResolvedValue([]);

    render(<ProgressDashboard />);

    await waitFor(() => {
      expect(screen.getByText("0%")).toBeInTheDocument();
    });

    expect(screen.getByText("No roadmap generated yet.")).toBeInTheDocument();
    expect(
      screen.getByText("No skills acquired yet. Complete weekly plans to see your skill progress here.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No timeline data available. Generate a roadmap to see your progress timeline.")
    ).toBeInTheDocument();
  });
});
