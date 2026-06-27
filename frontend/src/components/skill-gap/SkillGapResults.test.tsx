import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { SkillGapResults } from "./SkillGapResults";
import { SkillGapApiError } from "@/lib/api/skill-gap";
import type { SkillGapAnalysis } from "@/types/skill-gap";

// Mock only the async functions, keep the real SkillGapApiError class
jest.mock("@/lib/api/skill-gap", () => {
  const actual = jest.requireActual("@/lib/api/skill-gap");
  return {
    ...actual,
    getSkillGapResults: jest.fn(),
    runSkillGapAnalysis: jest.fn(),
  };
});

import { getSkillGapResults, runSkillGapAnalysis } from "@/lib/api/skill-gap";

const mockedGetResults = getSkillGapResults as jest.MockedFunction<typeof getSkillGapResults>;
const mockedRunAnalysis = runSkillGapAnalysis as jest.MockedFunction<typeof runSkillGapAnalysis>;

const mockAnalysisWithGaps: SkillGapAnalysis = {
  gaps: [
    {
      skill_name: "Kubernetes",
      category: "critical",
      current_proficiency: null,
      required_proficiency: "advanced",
    },
    {
      skill_name: "Docker",
      category: "critical",
      current_proficiency: "beginner",
      required_proficiency: "intermediate",
    },
    {
      skill_name: "CI/CD",
      category: "important",
      current_proficiency: "beginner",
      required_proficiency: "advanced",
    },
    {
      skill_name: "Terraform",
      category: "nice-to-have",
      current_proficiency: "intermediate",
      required_proficiency: "advanced",
    },
  ],
  all_requirements_met: false,
  advanced_specializations: null,
};

const mockAnalysisAllMet: SkillGapAnalysis = {
  gaps: [],
  all_requirements_met: true,
  advanced_specializations: [
    "Cloud Architecture",
    "Site Reliability Engineering",
    "Platform Engineering",
  ],
};

describe("SkillGapResults", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("shows loading state on initial render", async () => {
    mockedGetResults.mockImplementation(() => new Promise(() => {}));

    render(<SkillGapResults />);

    expect(screen.getByText("Analyzing your skill gaps...")).toBeInTheDocument();
  });

  it("displays skill gaps grouped by category", async () => {
    mockedGetResults.mockResolvedValue(mockAnalysisWithGaps);

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    });

    // Category sections are present (each category label appears in heading + badges)
    expect(screen.getByRole("heading", { name: /Critical/i })).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText("Docker")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: /Important/i })).toBeInTheDocument();
    expect(screen.getByText("CI/CD")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: /Nice to Have/i })).toBeInTheDocument();
    expect(screen.getByText("Terraform")).toBeInTheDocument();
  });

  it("shows skill name, category badge, and proficiency for each gap", async () => {
    mockedGetResults.mockResolvedValue(mockAnalysisWithGaps);

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    });

    // Kubernetes has null current proficiency - shows "None"
    const noneElements = screen.getAllByText("None");
    expect(noneElements.length).toBeGreaterThan(0);

    // Docker shows "Beginner" as current
    const beginnerElements = screen.getAllByText("Beginner");
    expect(beginnerElements.length).toBeGreaterThan(0);
  });

  it("shows all requirements met view with specialization suggestions", async () => {
    mockedGetResults.mockResolvedValue(mockAnalysisAllMet);

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("All Requirements Met!")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "Your current skills meet all the requirements for your target role."
      )
    ).toBeInTheDocument();

    expect(screen.getByText("Cloud Architecture")).toBeInTheDocument();
    expect(screen.getByText("Site Reliability Engineering")).toBeInTheDocument();
    expect(screen.getByText("Platform Engineering")).toBeInTheDocument();
  });

  it("shows error guidance for INCOMPLETE_PROFILE", async () => {
    mockedGetResults.mockRejectedValue(
      new SkillGapApiError("INCOMPLETE_PROFILE", "Profile is incomplete")
    );

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Prerequisites Missing")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "Please complete your profile with at least a job title and one skill before running the analysis."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Go to your profile to add your job title and skills.")
    ).toBeInTheDocument();
  });

  it("shows error guidance for NO_TARGET_ROLE", async () => {
    mockedGetResults.mockRejectedValue(
      new SkillGapApiError("NO_TARGET_ROLE", "No target role selected")
    );

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Prerequisites Missing")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "Please select a target role before running gap analysis."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Select a target role to proceed with the analysis.")
    ).toBeInTheDocument();
  });

  it("shows generic error for unknown error codes", async () => {
    mockedGetResults.mockRejectedValue(
      new SkillGapApiError("UNKNOWN", "Something went wrong")
    );

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Analysis Error")).toBeInTheDocument();
    });

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("runs analysis when Run Analysis button is clicked", async () => {
    mockedGetResults.mockResolvedValue(mockAnalysisWithGaps);
    mockedRunAnalysis.mockResolvedValue(mockAnalysisAllMet);

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /run skill gap analysis/i }));

    await waitFor(() => {
      expect(screen.getByText("All Requirements Met!")).toBeInTheDocument();
    });

    expect(mockedRunAnalysis).toHaveBeenCalledTimes(1);
  });

  it("disables button during loading", () => {
    mockedGetResults.mockImplementation(() => new Promise(() => {}));

    render(<SkillGapResults />);

    const button = screen.getByRole("button", { name: /run skill gap analysis/i });
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("Analyzing...");
  });

  it("displays gap counts per category", async () => {
    mockedGetResults.mockResolvedValue(mockAnalysisWithGaps);

    render(<SkillGapResults />);

    await waitFor(() => {
      expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    });

    // Check that category sections have aria-labels with correct counts
    const criticalGaps = screen.getByLabelText("Critical skill gaps");
    expect(criticalGaps.children.length).toBe(2);

    const importantGaps = screen.getByLabelText("Important skill gaps");
    expect(importantGaps.children.length).toBe(1);

    const niceToHaveGaps = screen.getByLabelText("Nice to Have skill gaps");
    expect(niceToHaveGaps.children.length).toBe(1);
  });
});
