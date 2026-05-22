import { fireEvent, render, screen } from "@testing-library/react";

import TutorialPage from "@/app/tutorial/page";

describe("tutorial flow", () => {
  test("renders an interactive commercial demo path", () => {
    render(<TutorialPage />);

    expect(screen.getByRole("heading", { name: "Tutorial" })).toBeInTheDocument();
    expect(screen.getByText("12 curated templates")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Inspect replay/ }));

    expect(screen.getByText("ledger integrity visible")).toBeInTheDocument();
    expect(screen.getByText("Planner conclusion")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare Plans" })).toHaveAttribute("href", "/monetization");
  });
});
