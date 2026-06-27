import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TargetRoleSelection } from "./TargetRoleSelection";
import * as targetRoleApi from "@/lib/api/target-role";

// Keep the actual TargetRoleApiError class so instanceof checks work
jest.mock("@/lib/api/target-role", () => {
  const actual = jest.requireActual("@/lib/api/target-role");
  return {
    ...actual,
    setTargetRole: jest.fn(),
    getTargetRoleRequirements: jest.fn(),
    updateTargetRoleSkills: jest.fn(),
    setCustomRole: jest.fn(),
  };
});

const mockGetRequirements = targetRoleApi.getTargetRoleRequirements as jest.MockedFunction<
  typeof targetRoleApi.getTargetRoleRequirements
>;
const mockSetTargetRole = targetRoleApi.setTargetRole as jest.MockedFunction<
  typeof targetRoleApi.setTargetRole
>;
const mockUpdateSkills = targetRoleApi.updateTargetRoleSkills as jest.MockedFunction<
  typeof targetRoleApi.updateTargetRoleSkills
>;
const mockSetCustomRole = targetRoleApi.setCustomRole as jest.MockedFunction<
  typeof targetRoleApi.setCustomRole
>;

describe("TargetRoleSelection", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the role title input form", () => {
    render(<TargetRoleSelection />);
    expect(screen.getByLabelText(/target role title/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /find role/i })).toBeInTheDocument();
  });

  it("validates empty role title", async () => {
    const user = userEvent.setup();
    render(<TargetRoleSelection />);

    await user.click(screen.getByRole("button", { name: /find role/i }));

    expect(screen.getByRole("alert")).toHaveTextContent("Role title is required");
  });

  it("validates role title exceeding 100 characters", async () => {
    const user = userEvent.setup();
    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "a".repeat(101));
    await user.click(screen.getByRole("button", { name: /find role/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Role title must be 100 characters or fewer"
    );
  });

  it("shows loading state while fetching requirements", async () => {
    const user = userEvent.setup();
    mockGetRequirements.mockImplementation(
      () => new Promise(() => {}) // never resolves
    );

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Software Engineer");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    expect(screen.getByText(/searching/i)).toBeInTheDocument();
  });

  it("displays skills for a recognized role", async () => {
    const user = userEvent.setup();
    mockGetRequirements.mockResolvedValue({
      role_title: "Software Engineer",
      recognized: true,
      skills: [
        { skill_name: "JavaScript", required_proficiency: "advanced", category: "critical" },
        { skill_name: "React", required_proficiency: "intermediate", category: "important" },
        { skill_name: "Node.js", required_proficiency: "intermediate", category: "important" },
        { skill_name: "SQL", required_proficiency: "beginner", category: "nice-to-have" },
        { skill_name: "TypeScript", required_proficiency: "advanced", category: "critical" },
      ],
    });

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Software Engineer");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByText("JavaScript")).toBeInTheDocument();
    });
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText(/role recognized/i)).toBeInTheDocument();
  });

  it("shows custom role form for unrecognized role", async () => {
    const user = userEvent.setup();
    mockGetRequirements.mockResolvedValue({
      role_title: "Space Cowboy",
      recognized: false,
      skills: [],
    });

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Space Cowboy");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByText(/unrecognized role/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/role responsibilities/i)).toBeInTheDocument();
  });

  it("shows API error when request fails", async () => {
    const user = userEvent.setup();
    mockGetRequirements.mockRejectedValue(
      new targetRoleApi.TargetRoleApiError("AI_UNAVAILABLE", "The AI service is temporarily unavailable.")
    );

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Data Scientist");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "The AI service is temporarily unavailable."
      );
    });
  });

  it("saves a recognized role successfully", async () => {
    const user = userEvent.setup();
    const savedRole = {
      id: "123",
      user_id: "456",
      role_title: "Software Engineer",
      is_recognized: true,
      skills: [
        { skill_name: "JavaScript", required_proficiency: "advanced" as const, category: "critical" as const },
        { skill_name: "React", required_proficiency: "intermediate" as const, category: "important" as const },
        { skill_name: "Node.js", required_proficiency: "intermediate" as const, category: "important" as const },
        { skill_name: "SQL", required_proficiency: "beginner" as const, category: "nice-to-have" as const },
        { skill_name: "TypeScript", required_proficiency: "advanced" as const, category: "critical" as const },
      ],
    };

    mockGetRequirements.mockResolvedValue({
      role_title: "Software Engineer",
      recognized: true,
      skills: savedRole.skills,
    });
    mockSetTargetRole.mockResolvedValue(savedRole);
    mockUpdateSkills.mockResolvedValue(savedRole);

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Software Engineer");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByText("JavaScript")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /confirm target role/i }));

    await waitFor(() => {
      expect(screen.getByText(/target role set successfully/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/software engineer/i)).toBeInTheDocument();
  });

  it("allows changing role after successful save", async () => {
    const user = userEvent.setup();
    const savedRole = {
      id: "123",
      user_id: "456",
      role_title: "Software Engineer",
      is_recognized: true,
      skills: [
        { skill_name: "JavaScript", required_proficiency: "advanced" as const, category: "critical" as const },
        { skill_name: "React", required_proficiency: "intermediate" as const, category: "important" as const },
        { skill_name: "Node.js", required_proficiency: "intermediate" as const, category: "important" as const },
        { skill_name: "SQL", required_proficiency: "beginner" as const, category: "nice-to-have" as const },
        { skill_name: "TypeScript", required_proficiency: "advanced" as const, category: "critical" as const },
      ],
    };

    mockGetRequirements.mockResolvedValue({
      role_title: "Software Engineer",
      recognized: true,
      skills: savedRole.skills,
    });
    mockSetTargetRole.mockResolvedValue(savedRole);
    mockUpdateSkills.mockResolvedValue(savedRole);

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Software Engineer");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByText("JavaScript")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /confirm target role/i }));

    await waitFor(() => {
      expect(screen.getByText(/target role set successfully/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /change target role/i }));
    expect(screen.getByLabelText(/target role title/i)).toBeInTheDocument();
  });
});

describe("CustomRoleForm integration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("validates minimum 3 skills and non-empty responsibilities", async () => {
    const user = userEvent.setup();
    mockGetRequirements.mockResolvedValue({
      role_title: "Space Cowboy",
      recognized: false,
      skills: [],
    });

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Space Cowboy");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByText(/unrecognized role/i)).toBeInTheDocument();
    });

    // Try to submit without adding skills or responsibilities
    await user.click(screen.getByRole("button", { name: /save custom role/i }));

    expect(screen.getByText(/at least 3 skills are required/i)).toBeInTheDocument();
    expect(screen.getByText(/responsibilities description is required/i)).toBeInTheDocument();
  });

  it("submits custom role when valid data provided", async () => {
    const user = userEvent.setup();
    const savedRole = {
      id: "789",
      user_id: "456",
      role_title: "Space Cowboy",
      is_recognized: false,
      skills: [
        { skill_name: "Piloting", required_proficiency: "advanced" as const, category: "critical" as const },
        { skill_name: "Navigation", required_proficiency: "intermediate" as const, category: "important" as const },
        { skill_name: "Diplomacy", required_proficiency: "beginner" as const, category: "nice-to-have" as const },
      ],
    };

    mockGetRequirements.mockResolvedValue({
      role_title: "Space Cowboy",
      recognized: false,
      skills: [],
    });
    mockSetCustomRole.mockResolvedValue(savedRole);

    render(<TargetRoleSelection />);

    const input = screen.getByLabelText(/target role title/i);
    await user.type(input, "Space Cowboy");
    await user.click(screen.getByRole("button", { name: /find role/i }));

    await waitFor(() => {
      expect(screen.getByText(/unrecognized role/i)).toBeInTheDocument();
    });

    // Add 3 skills
    const skillInput = screen.getByPlaceholderText(/e\.g\., react/i);
    await user.type(skillInput, "Piloting");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await user.type(skillInput, "Navigation");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await user.type(skillInput, "Diplomacy");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    // Add responsibilities
    const respInput = screen.getByLabelText(/role responsibilities/i);
    await user.type(respInput, "Exploring the galaxy and mediating conflicts");

    // Submit
    await user.click(screen.getByRole("button", { name: /save custom role/i }));

    await waitFor(() => {
      expect(screen.getByText(/target role set successfully/i)).toBeInTheDocument();
    });
    expect(mockSetCustomRole).toHaveBeenCalledWith({
      role_title: "Space Cowboy",
      skills: expect.arrayContaining([
        expect.objectContaining({ skill_name: "Piloting" }),
        expect.objectContaining({ skill_name: "Navigation" }),
        expect.objectContaining({ skill_name: "Diplomacy" }),
      ]),
      responsibilities: "Exploring the galaxy and mediating conflicts",
    });
  });
});
