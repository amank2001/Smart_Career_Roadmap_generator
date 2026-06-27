import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InterviewPrep } from "./InterviewPrep";
import { InterviewApiError } from "@/lib/api/interview";
import type { InterviewSession } from "@/types/interview";

jest.mock("@/lib/api/interview", () => {
  const actual = jest.requireActual("@/lib/api/interview");
  return {
    ...actual,
    generateInterviewQuestions: jest.fn(),
    submitAnswer: jest.fn(),
  };
});

import { generateInterviewQuestions, submitAnswer } from "@/lib/api/interview";

const mockedGenerate = generateInterviewQuestions as jest.MockedFunction<
  typeof generateInterviewQuestions
>;
const mockedSubmitAnswer = submitAnswer as jest.MockedFunction<typeof submitAnswer>;

const mockSession: InterviewSession = {
  id: "session-1",
  created_at: "2024-01-01T00:00:00Z",
  questions: [
    {
      id: "q1",
      question: "Explain how containers work in Docker.",
      category: "technical",
      difficulty: "beginner",
      model_answer: "Containers are lightweight isolated processes...",
      evaluation_criteria: ["Isolation", "Namespaces", "Cgroups"],
    },
    {
      id: "q2",
      question: "Tell me about a time you led a team through a difficult challenge.",
      category: "behavioral",
      difficulty: "intermediate",
      model_answer: "Use the STAR method to describe...",
      evaluation_criteria: ["Situation", "Task", "Action", "Result"],
    },
    {
      id: "q3",
      question: "Design a URL shortener service.",
      category: "system-design",
      difficulty: "advanced",
      model_answer: "A URL shortener needs a hash function...",
      evaluation_criteria: ["Scalability", "Storage", "Redirection"],
    },
  ],
};

describe("InterviewPrep", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("shows idle state with generate button", () => {
    render(<InterviewPrep />);

    expect(screen.getByText("Interview Preparation")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/click "generate questions"/i)
    ).toBeInTheDocument();
  });

  it("shows loading state when generating questions", async () => {
    mockedGenerate.mockImplementation(() => new Promise(() => {}));

    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    expect(screen.getByText("Generating interview questions...")).toBeInTheDocument();
  });

  it("displays questions with category and difficulty badges after generation", async () => {
    mockedGenerate.mockResolvedValue(mockSession);

    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    await waitFor(() => {
      expect(screen.getByText("Questions (3)")).toBeInTheDocument();
    });

    // Category badges
    expect(screen.getByText("Technical")).toBeInTheDocument();
    expect(screen.getByText("Behavioral")).toBeInTheDocument();
    expect(screen.getByText("System Design")).toBeInTheDocument();

    // Difficulty badges
    expect(screen.getByText("Beginner")).toBeInTheDocument();
    expect(screen.getByText("Intermediate")).toBeInTheDocument();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  it("selects and shows answer form for the first question by default", async () => {
    mockedGenerate.mockResolvedValue(mockSession);

    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    // Verify the main content area shows the first question
    const mainArea = await waitFor(() => {
      const area = screen.getByRole("main", { name: /active question and answer/i });
      expect(
        within(area).getByText("Explain how containers work in Docker.")
      ).toBeInTheDocument();
      return area;
    });

    // Answer input should be visible
    expect(screen.getByLabelText("Your Answer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit Answer" })).toBeInTheDocument();
  });

  it("submits an answer and shows feedback", async () => {
    mockedGenerate.mockResolvedValue(mockSession);
    mockedSubmitAnswer.mockResolvedValue({
      strengths: ["Good understanding of isolation"],
      areas_for_improvement: ["Could elaborate on namespaces"],
      overall_assessment: "Solid beginner answer with room to grow.",
    });

    const user = userEvent.setup();
    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Your Answer")).toBeInTheDocument();
    });

    await user.type(
      screen.getByLabelText("Your Answer"),
      "Containers use OS-level virtualization..."
    );

    await user.click(screen.getByRole("button", { name: "Submit Answer" }));

    await waitFor(() => {
      expect(
        screen.getByText("Solid beginner answer with room to grow.")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Good understanding of isolation")).toBeInTheDocument();
    expect(screen.getByText("Could elaborate on namespaces")).toBeInTheDocument();
  });

  it("shows error state when generation fails", async () => {
    mockedGenerate.mockRejectedValue(
      new InterviewApiError("AI_UNAVAILABLE", "AI service is unavailable")
    );

    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    await waitFor(() => {
      expect(screen.getByText("Failed to Generate Questions")).toBeInTheDocument();
    });

    expect(screen.getByText("AI service is unavailable")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("allows selecting a different question", async () => {
    mockedGenerate.mockResolvedValue(mockSession);

    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    await waitFor(() => {
      expect(screen.getByText("Questions (3)")).toBeInTheDocument();
    });

    // Click the second question
    fireEvent.click(
      screen.getByRole("button", {
        name: /question 2/i,
      })
    );

    // Verify the main content area shows the selected question
    const mainArea = screen.getByRole("main", { name: /active question and answer/i });
    await waitFor(() => {
      expect(
        within(mainArea).getByText(
          "Tell me about a time you led a team through a difficult challenge."
        )
      ).toBeInTheDocument();
    });
  });

  it("shows model answer when toggled", async () => {
    mockedGenerate.mockResolvedValue(mockSession);

    render(<InterviewPrep />);

    fireEvent.click(
      screen.getByRole("button", { name: /generate mock interview questions/i })
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Your Answer")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Show Model Answer" }));

    expect(
      screen.getByText("Containers are lightweight isolated processes...")
    ).toBeInTheDocument();
  });
});
