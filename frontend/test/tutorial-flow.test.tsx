import { fireEvent, render, screen } from "@testing-library/react";

import TutorialPage from "@/app/tutorial/page";

describe("tutorial flow", () => {
  test("renders an interactive commercial demo path", () => {
    render(<TutorialPage />);

    expect(screen.getByRole("heading", { name: "Tutorial" })).toBeInTheDocument();
    expect(screen.getByText("PR release gate")).toBeInTheDocument();
    expect(screen.getByText(/Let enterprises connect agents to CI\/CD/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Audit replay/ }));

    expect(screen.getByText("audit report")).toBeInTheDocument();
    expect(screen.getByText("Policy gate decision")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare Plans" })).toHaveAttribute("href", "/monetization");
  });
});
