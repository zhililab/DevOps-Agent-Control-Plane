import { render, screen } from "@testing-library/react";

import DashboardPage from "@/app/dashboard/page";
import HistoryPage from "@/app/history/page";
import KnowledgePage from "@/app/knowledge/page";
import ProfilePage from "@/app/profile/page";
import ReflectionPage from "@/app/reflection/page";
import TechnicalAnalysisPage from "@/app/technical-analysis/page";
import TemplatesPage from "@/app/templates/page";
import TodayPage from "@/app/today/page";

describe("core pages", () => {
  test("renders dashboard", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
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

  test("renders templates", () => {
    render(<TemplatesPage />);
    expect(screen.getByRole("heading", { name: "Templates", level: 2 })).toBeInTheDocument();
  });
});
