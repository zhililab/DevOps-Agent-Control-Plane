import { render, screen } from "@testing-library/react";

import DashboardPage from "@/app/dashboard/page";
import EvaluationPage from "@/app/evaluation/page";
import HistoryPage from "@/app/history/page";
import KnowledgePage from "@/app/knowledge/page";
import MonetizationPage from "@/app/monetization/page";
import OrchestratePage from "@/app/orchestrate/page";
import OrchestrationsPage from "@/app/orchestrations/page";
import ProfilePage from "@/app/profile/page";
import ReflectionPage from "@/app/reflection/page";
import TechnicalAnalysisPage from "@/app/technical-analysis/page";
import TemplatesPage from "@/app/templates/page";
import TodayPage from "@/app/today/page";
import TutorialPage from "@/app/tutorial/page";

describe("core pages", () => {
  test("renders dashboard", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: "Control Dashboard" })).toBeInTheDocument();
  });

  test("renders agent quality lab", () => {
    render(<EvaluationPage />);
    expect(screen.getByRole("heading", { name: "Agent Quality Lab" })).toBeInTheDocument();
  });

  test("renders profile", () => {
    render(<ProfilePage />);
    expect(screen.getByRole("heading", { name: "Profile" })).toBeInTheDocument();
  });

  test("renders today", () => {
    render(<TodayPage />);
    expect(screen.getByRole("heading", { name: "Today" })).toBeInTheDocument();
  });

  test("renders reflection", () => {
    render(<ReflectionPage />);
    expect(screen.getByRole("heading", { name: "Reflection" })).toBeInTheDocument();
  });

  test("renders history", () => {
    render(<HistoryPage />);
    expect(screen.getByRole("heading", { name: "History" })).toBeInTheDocument();
  });

  test("renders technical analysis", () => {
    render(<TechnicalAnalysisPage />);
    expect(screen.getByRole("heading", { name: "Technical Analysis" })).toBeInTheDocument();
  });

  test("renders knowledge", () => {
    render(<KnowledgePage />);
    expect(screen.getByRole("heading", { name: "Knowledge" })).toBeInTheDocument();
  });

  test("renders orchestrate", () => {
    render(<OrchestratePage />);
    expect(screen.getByRole("heading", { name: "Workflow Orchestrator" })).toBeInTheDocument();
  });

  test("renders orchestrations", () => {
    render(<OrchestrationsPage />);
    expect(screen.getByRole("heading", { name: "Orchestration History" })).toBeInTheDocument();
  });

  test("renders monetization", () => {
    render(<MonetizationPage />);
    expect(screen.getByRole("heading", { name: "Plans & Usage" })).toBeInTheDocument();
  });

  test("renders tutorial", () => {
    render(<TutorialPage />);
    expect(screen.getByRole("heading", { name: "Tutorial" })).toBeInTheDocument();
  });

  test("renders templates", () => {
    render(<TemplatesPage />);
    expect(screen.getByRole("heading", { name: "Templates", level: 2 })).toBeInTheDocument();
  });
});
