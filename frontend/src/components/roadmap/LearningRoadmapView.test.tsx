import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LearningRoadmapView } from "./LearningRoadmapView";
import * as roadmapApi from "@/lib/api/roadmap";

jest.mock("@/lib/api/roadmap", () => {
  const actual = jest.requireActual("@/lib/api/roadmap");
  return {
    ...actual,
    getRoadmap: jest.fn(),
    generateRoadmap: jest.fn(),
    updateWeeklyHours: jest.fn(),
  };
});

const mockGetRoadmap = roadmapApi.getRoadmap as jest.MockedFunction<typeof roadmapApi.getRoadmap>;
const mockGenerateRoadmap = roadmapApi.generateRoadmap as jest.MockedFunction<typeof roadmapApi.generateRoadmap>;
const mockUpdateWeeklyHours = roadmapApi.updateWeeklyHours as jest.MockedFunction<typeof roadmapApi.updateWeeklyHours>;

const sampleRoadmap = {
  id: "roadmap-1",
  user_id: "user-1",
  topics: [
    {
      id: "topic-1",
      skill_name: "TypeScript",
      category: "critical" as const,
      proficiency_target: "advanced" as const,
      prerequisites: [],
      resources: [
        { title: "TypeScript Deep Dive", type: "book" as const, url: "https://example.com/ts" },
        { title: "TS Official Docs", type: "documentation" as const, url: null },
      ],
      estimated_hours: 20,
      order: 1,
    },
    {
      id: "topic-2",
      skill_name: "React",
      category: "important" as const,
      proficiency_target: "intermediate" as const,
      prerequisites: ["topic-1"],
      resources: [
        { title: "React Tutorial", type: "tutorial" as const, url: "https://example.com/react" },
        { title: "React Course", type: "course" as const, url: null },
      ],
      estimated_hours: 15,
      order: 2,
    },
  ],
  total_weeks: 4,
  weekly_study_hours: 10,
};

describe("LearningRoadmapView", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading state while fetching roadmap", () => {
    mockGetRoadmap.mockImplementation(() => new Promise(() => {}));
    render(<LearningRoadmapView />);
    expect(screen.getByText(/building your learning roadmap/i)).toBeInTheDocument();
  });

  it("displays roadmap topics with resources on success", async () => {
    mockGetRoadmap.mockResolvedValue(sampleRoadmap);
    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript Deep Dive")).toBeInTheDocument();
    expect(screen.getByText("React Tutorial")).toBeInTheDocument();
    expect(screen.getByText(/2 topics/)).toBeInTheDocument();
    expect(screen.getByText(/4 weeks estimated/)).toBeInTheDocument();
  });

  it("shows prerequisite error when gap analysis is missing", async () => {
    mockGetRoadmap.mockRejectedValue(
      new roadmapApi.RoadmapApiError("NO_GAP_ANALYSIS", "Please run a skill gap analysis first")
    );
    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText(/prerequisite missing/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/skill gap analysis first/i)).toBeInTheDocument();
  });

  it("shows generic error for other failures", async () => {
    mockGetRoadmap.mockRejectedValue(
      new roadmapApi.RoadmapApiError("AI_UNAVAILABLE", "AI service is unavailable")
    );
    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText("AI service is unavailable")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("generates roadmap when button is clicked", async () => {
    const user = userEvent.setup();
    mockGetRoadmap.mockRejectedValue(
      new roadmapApi.RoadmapApiError("NOT_FOUND", "No roadmap found")
    );
    mockGenerateRoadmap.mockResolvedValue(sampleRoadmap);

    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /generate learning roadmap/i }));

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });
    expect(mockGenerateRoadmap).toHaveBeenCalled();
  });

  it("recalculates roadmap when weekly hours change", async () => {
    const user = userEvent.setup();
    mockGetRoadmap.mockResolvedValue(sampleRoadmap);
    const updatedRoadmap = { ...sampleRoadmap, weekly_study_hours: 20, total_weeks: 2 };
    mockUpdateWeeklyHours.mockResolvedValue(updatedRoadmap);

    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });

    const hoursInput = screen.getByLabelText(/weekly study hours/i);
    await user.clear(hoursInput);
    await user.type(hoursInput, "20");
    await user.tab(); // blur to trigger submit

    await waitFor(() => {
      expect(mockUpdateWeeklyHours).toHaveBeenCalledWith({ weekly_study_hours: 20 });
    });
    await waitFor(() => {
      expect(screen.getByText(/2 weeks estimated/)).toBeInTheDocument();
    });
  });

  it("shows validation error for invalid weekly hours", async () => {
    const user = userEvent.setup();
    mockGetRoadmap.mockResolvedValue(sampleRoadmap);

    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });

    const hoursInput = screen.getByLabelText(/weekly study hours/i);
    await user.clear(hoursInput);
    await user.type(hoursInput, "50");
    await user.tab();

    expect(screen.getByText(/weekly study hours must be between 1 and 40/i)).toBeInTheDocument();
    expect(mockUpdateWeeklyHours).not.toHaveBeenCalled();
  });

  it("displays learning resources with correct types", async () => {
    mockGetRoadmap.mockResolvedValue(sampleRoadmap);
    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript Deep Dive")).toBeInTheDocument();
    });
    expect(screen.getByText("(book)")).toBeInTheDocument();
    expect(screen.getByText("(documentation)")).toBeInTheDocument();
    expect(screen.getByText("(tutorial)")).toBeInTheDocument();
    expect(screen.getByText("(course)")).toBeInTheDocument();
  });

  it("renders resource links when URL is provided", async () => {
    mockGetRoadmap.mockResolvedValue(sampleRoadmap);
    render(<LearningRoadmapView />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript Deep Dive")).toBeInTheDocument();
    });

    const link = screen.getByRole("link", { name: /typescript deep dive/i });
    expect(link).toHaveAttribute("href", "https://example.com/ts");
    expect(link).toHaveAttribute("target", "_blank");
  });
});
