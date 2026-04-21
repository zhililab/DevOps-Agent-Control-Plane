import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import DashboardPage from "@/app/dashboard/page";

describe("dashboard graph interaction", () => {
  test("supports keyboard focus switching and consistent active states", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Focus: All. Use Left/Right arrows to switch.")).toBeInTheDocument();
    });

    const filterGroup = screen.getByRole("group", { name: "Graph focus filter" });
    const allButton = screen.getByRole("button", { name: "Focus All" });
    const planButton = screen.getByRole("button", { name: "Focus Plan" });
    const reflectionButton = screen.getByRole("button", { name: "Focus Reflection" });

    expect(allButton).toHaveAttribute("aria-pressed", "true");

    fireEvent.keyDown(filterGroup, { key: "ArrowRight" });
    expect(planButton).toHaveAttribute("aria-pressed", "true");
    expect(allButton).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("img", { name: "Graph focused on Plan" })).toBeInTheDocument();

    const reflectionNodeLabel = screen
      .getAllByText("Reflection")
      .find((item) => item.tagName.toLowerCase() === "text");
    const reflectionNode = reflectionNodeLabel?.closest("g");
    expect(reflectionNode).toBeTruthy();
    expect(reflectionNode).toHaveClass("graph-node-dim");

    fireEvent.keyDown(filterGroup, { key: "End" });
    expect(screen.getByRole("button", { name: "Focus Analysis" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.keyDown(filterGroup, { key: "Home" });
    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(reflectionButton).toHaveAttribute("aria-pressed", "false");
  });
});
