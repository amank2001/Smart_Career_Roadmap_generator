import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProjectSuggestions } from "./ProjectSuggestions";
import { ProjectApiError } from "@/lib/api/projects";
import type { ProjectSuggestion } from "@/types/project";

jest.mock("@/lib/api/projects", () => {
  const actual = jest.requireActual("@/lib/api/projects");
  return {
    ...actual,
    getProjectSuggestions: jest.fn(),
    completeProject: jest.fn(),
    dismissProject: jest.fn(),
    skipAllProjects: jest.fn(),
  };
});

import {
  getProjectSuggestions,
  completeProject,
  dismissProject,
  skipAllProjects,
} from "@/lib/api/projects";

const mockedGetProjects = getProjectSuggestions as jest.MockedFunction<
  typeof getProjectSuggestions
>;
const mockedComplete = completeProject as jest.MockedFunction<typeof completeProject>;
const mockedDismiss = dismissProject as jest.MockedFunction<typeof dismissProject>;
const mockedSkipAll = skipAllProjects as jest.MockedFunction<typeof skipAllProjects>;

const mockProjects: ProjectSuggestion[] = [
  {
    id: "p1",
    title: "Build a REST API with Node.js",
    objectives: ["Create CRUD endpoints", "Implement authentication"],
    deliverables: ["Working API", "API documentation"],
    technologies: ["Node.js", "Express", "PostgreSQL"],
    estimated_weeks: 2,
    complexity: "intermediate",
    completed: false,
    outcome_description: null,
    dismissed: false,
  },
  {
    id: "p2",
    title: "Create a Docker Container Setup",
    objectives: ["Containerize an application", "Use multi-stage builds"],
    deliverables: ["Dockerfile", "docker-compose.yml"],
    technologies: ["Docker", "Docker Compose"],
    estimated_weeks: 1,
    complexity: "beginner",
    completed: false,
    outcome_description: null,
    dismissed: false,
  },
];

describe("ProjectSuggestions", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("shows loading state initially", () => {
    mockedGetProjects.mockImplementation(() => new Promise(() => {}));

    render(<ProjectSuggestions planId="plan-1" />);

    expect(screen.getByText("Loading project suggestions...")).toBeInTheDocument();
  });

  it("displays project cards with objectives, deliverables, and technologies", async () => {
    mockedGetProjects.mockResolvedValue(mockProjects);

    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(screen.getByText("Build a REST API with Node.js")).toBeInTheDocument();
    });

    expect(screen.getByText("Create a Docker Container Setup")).toBeInTheDocument();

    // Objectives
    expect(screen.getByText("Create CRUD endpoints")).toBeInTheDocument();
    expect(screen.getByText("Implement authentication")).toBeInTheDocument();

    // Deliverables
    expect(screen.getByText("Working API")).toBeInTheDocument();
    expect(screen.getByText("API documentation")).toBeInTheDocument();

    // Technologies
    expect(screen.getByText("Node.js")).toBeInTheDocument();
    expect(screen.getByText("Express")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument();

    // Complexity badges
    expect(screen.getByText("Intermediate")).toBeInTheDocument();
    expect(screen.getByText("Beginner")).toBeInTheDocument();

    // Estimated time
    expect(screen.getByText("2 weeks")).toBeInTheDocument();
    expect(screen.getByText("1 week")).toBeInTheDocument();
  });

  it("shows error state when fetching fails", async () => {
    mockedGetProjects.mockRejectedValue(
      new ProjectApiError("NOT_FOUND", "No projects found")
    );

    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
    });

    expect(screen.getByText("No projects found")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("allows marking a project complete with outcome text", async () => {
    mockedGetProjects.mockResolvedValue(mockProjects);
    mockedComplete.mockResolvedValue({
      ...mockProjects[0],
      completed: true,
      outcome_description: "Built a full REST API with JWT auth",
    });

    const user = userEvent.setup();
    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(screen.getByText("Build a REST API with Node.js")).toBeInTheDocument();
    });

    // Click "Complete Project" on the first card
    const completeButtons = screen.getAllByRole("button", { name: "Complete Project" });
    await user.click(completeButtons[0]);

    // Outcome form should appear
    expect(screen.getByLabelText("Describe your outcome")).toBeInTheDocument();

    // Type outcome (under 500 chars)
    await user.type(
      screen.getByLabelText("Describe your outcome"),
      "Built a full REST API with JWT auth"
    );

    // Submit
    await user.click(screen.getByRole("button", { name: "Mark Complete" }));

    await waitFor(() => {
      expect(screen.getByText("Completed")).toBeInTheDocument();
    });

    expect(mockedComplete).toHaveBeenCalledWith(
      "p1",
      "Built a full REST API with JWT auth"
    );
  });

  it("shows character count and validates max 500 chars", async () => {
    mockedGetProjects.mockResolvedValue(mockProjects);

    const user = userEvent.setup();
    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(screen.getByText("Build a REST API with Node.js")).toBeInTheDocument();
    });

    const completeButtons = screen.getAllByRole("button", { name: "Complete Project" });
    await user.click(completeButtons[0]);

    const textarea = screen.getByLabelText("Describe your outcome");
    expect(textarea).toHaveAttribute("maxLength", "500");

    // Verify character counter is shown
    expect(screen.getByText("0/500")).toBeInTheDocument();
  });

  it("allows dismissing a project", async () => {
    mockedGetProjects.mockResolvedValue(mockProjects);
    mockedDismiss.mockResolvedValue({
      ...mockProjects[0],
      dismissed: true,
    });

    const user = userEvent.setup();
    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(screen.getByText("Build a REST API with Node.js")).toBeInTheDocument();
    });

    const dismissButtons = screen.getAllByRole("button", { name: "Dismiss" });
    await user.click(dismissButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Dismissed")).toBeInTheDocument();
    });

    expect(mockedDismiss).toHaveBeenCalledWith("p1");
  });

  it("allows skipping all projects", async () => {
    mockedGetProjects.mockResolvedValue(mockProjects);
    mockedSkipAll.mockResolvedValue(undefined);

    const user = userEvent.setup();
    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(screen.getByText("Build a REST API with Node.js")).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /skip all project suggestions/i })
    );

    await waitFor(() => {
      expect(
        screen.getByText(/all projects skipped/i)
      ).toBeInTheDocument();
    });

    expect(mockedSkipAll).toHaveBeenCalledWith("plan-1");
  });

  it("shows 'proceed' message when all projects are handled", async () => {
    const allDoneProjects: ProjectSuggestion[] = [
      { ...mockProjects[0], completed: true, outcome_description: "Done!" },
      { ...mockProjects[1], dismissed: true },
    ];
    mockedGetProjects.mockResolvedValue(allDoneProjects);

    render(<ProjectSuggestions planId="plan-1" />);

    await waitFor(() => {
      expect(
        screen.getByText(/all projects handled/i)
      ).toBeInTheDocument();
    });
  });
});
