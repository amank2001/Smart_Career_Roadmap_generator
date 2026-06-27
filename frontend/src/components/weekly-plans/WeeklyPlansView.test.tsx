import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WeeklyPlansView } from "./WeeklyPlansView";
import * as weeklyPlansApi from "@/lib/api/weekly-plans";

jest.mock("@/lib/api/weekly-plans", () => {
  const actual = jest.requireActual("@/lib/api/weekly-plans");
  return {
    ...actual,
    getWeeklyPlans: jest.fn(),
    getCurrentWeeklyPlan: jest.fn(),
    markTaskComplete: jest.fn(),
    adjustForDelay: jest.fn(),
  };
});

const mockGetWeeklyPlans = weeklyPlansApi.getWeeklyPlans as jest.MockedFunction<
  typeof weeklyPlansApi.getWeeklyPlans
>;
const mockMarkTaskComplete = weeklyPlansApi.markTaskComplete as jest.MockedFunction<
  typeof weeklyPlansApi.markTaskComplete
>;
const mockAdjustForDelay = weeklyPlansApi.adjustForDelay as jest.MockedFunction<
  typeof weeklyPlansApi.adjustForDelay
>;

const samplePlans = [
  {
    id: "plan-1",
    roadmap_id: "roadmap-1",
    week_number: 1,
    status: "completed" as const,
    tasks: [
      {
        id: "task-1",
        description: "Learn TypeScript basics",
        estimated_hours: 3,
        skill_name: "TypeScript",
        completion_criterion: "Complete TypeScript tutorial",
        completed: true,
      },
      {
        id: "task-2",
        description: "Build a TS project",
        estimated_hours: 4,
        skill_name: "TypeScript",
        completion_criterion: "Create a working TS app",
        completed: true,
      },
      {
        id: "task-3",
        description: "Review TS advanced types",
        estimated_hours: 3,
        skill_name: "TypeScript",
        completion_criterion: "Summarize generics and utility types",
        completed: true,
      },
    ],
    is_practical_milestone: false,
  },
  {
    id: "plan-2",
    roadmap_id: "roadmap-1",
    week_number: 2,
    status: "in-progress" as const,
    tasks: [
      {
        id: "task-4",
        description: "Learn React hooks",
        estimated_hours: 4,
        skill_name: "React",
        completion_criterion: "Build a component using useState and useEffect",
        completed: false,
      },
      {
        id: "task-5",
        description: "Study React state management",
        estimated_hours: 3,
        skill_name: "React",
        completion_criterion: "Implement Context API example",
        completed: false,
      },
      {
        id: "task-6",
        description: "React testing basics",
        estimated_hours: 3,
        skill_name: "React",
        completion_criterion: "Write tests for a component",
        completed: false,
      },
    ],
    is_practical_milestone: true,
  },
  {
    id: "plan-3",
    roadmap_id: "roadmap-1",
    week_number: 3,
    status: "upcoming" as const,
    tasks: [
      {
        id: "task-7",
        description: "Learn Node.js fundamentals",
        estimated_hours: 5,
        skill_name: "Node.js",
        completion_criterion: "Build a REST API",
        completed: false,
      },
      {
        id: "task-8",
        description: "Database basics",
        estimated_hours: 3,
        skill_name: "SQL",
        completion_criterion: "Write CRUD queries",
        completed: false,
      },
      {
        id: "task-9",
        description: "API design",
        estimated_hours: 2,
        skill_name: "Node.js",
        completion_criterion: "Document API endpoints",
        completed: false,
      },
    ],
    is_practical_milestone: false,
  },
];

describe("WeeklyPlansView", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading state while fetching plans", () => {
    mockGetWeeklyPlans.mockImplementation(() => new Promise(() => {}));
    render(<WeeklyPlansView />);
    expect(screen.getByText(/loading weekly plans/i)).toBeInTheDocument();
  });

  it("displays weekly plans grouped by status", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Week 1")).toBeInTheDocument();
    });
    expect(screen.getByText("Week 2")).toBeInTheDocument();
    expect(screen.getByText("Week 3")).toBeInTheDocument();
  });

  it("shows plan statuses correctly in timeline", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText(/1 of 3 weeks completed/i)).toBeInTheDocument();
    });
  });

  it("shows visual timeline with plan statuses", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByLabelText(/week 1: completed/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/week 2: in-progress/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/week 3: upcoming/i)).toBeInTheDocument();
  });

  it("displays tasks with completion criteria", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Learn React hooks")).toBeInTheDocument();
    });
    expect(screen.getByText(/build a component using usestate and useeffect/i)).toBeInTheDocument();
  });

  it("marks a task as complete", async () => {
    const user = userEvent.setup();
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);

    const updatedPlan = {
      ...samplePlans[1],
      tasks: [
        { ...samplePlans[1].tasks[0], completed: true },
        samplePlans[1].tasks[1],
        samplePlans[1].tasks[2],
      ],
    };
    mockMarkTaskComplete.mockResolvedValue(updatedPlan);

    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Learn React hooks")).toBeInTheDocument();
    });

    const checkbox = screen.getByLabelText(/mark "learn react hooks" as complete/i);
    await user.click(checkbox);

    await waitFor(() => {
      expect(mockMarkTaskComplete).toHaveBeenCalledWith("plan-2", "task-4");
    });
  });

  it("disables task checkboxes for non-active plans", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Learn Node.js fundamentals")).toBeInTheDocument();
    });

    const upcomingCheckbox = screen.getByLabelText(/mark "learn node.js fundamentals" as complete/i);
    expect(upcomingCheckbox).toBeDisabled();
  });

  it("shows delay adjustment prompt when button is clicked", async () => {
    const user = userEvent.setup();
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Week 2")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /report a delay/i }));

    expect(screen.getByText(/adjust for delay/i)).toBeInTheDocument();
    expect(screen.getByText(/redistribute remaining tasks/i)).toBeInTheDocument();
  });

  it("adjusts plans when delay adjustment is confirmed", async () => {
    const user = userEvent.setup();
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    mockAdjustForDelay.mockResolvedValue({
      plans: samplePlans,
      message: "Plans adjusted successfully",
    });

    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Week 2")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /report a delay/i }));
    await user.click(screen.getByRole("button", { name: /adjust plans/i }));

    await waitFor(() => {
      expect(mockAdjustForDelay).toHaveBeenCalled();
    });
  });

  it("shows roadmap completion summary when all plans are completed", async () => {
    const allCompleted = samplePlans.map((p) => ({
      ...p,
      status: "completed" as const,
      tasks: p.tasks.map((t) => ({ ...t, completed: true })),
    }));
    mockGetWeeklyPlans.mockResolvedValue(allCompleted);

    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText(/roadmap complete/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/completed all 3 weeks/i)).toBeInTheDocument();
  });

  it("shows error state with retry button", async () => {
    mockGetWeeklyPlans.mockRejectedValue(
      new weeklyPlansApi.WeeklyPlansApiError("UNKNOWN", "Server error")
    );
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("marks practical milestones with a badge", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(screen.getByText("Milestone")).toBeInTheDocument();
    });
  });

  it("shows progress bar for in-progress plans", async () => {
    mockGetWeeklyPlans.mockResolvedValue(samplePlans);
    render(<WeeklyPlansView />);

    await waitFor(() => {
      expect(
        screen.getByRole("progressbar", { name: /0 of 3 tasks completed/i })
      ).toBeInTheDocument();
    });
  });
});
