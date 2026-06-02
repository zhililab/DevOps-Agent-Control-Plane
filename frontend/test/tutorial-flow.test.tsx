import { fireEvent, render, screen } from "@testing-library/react";

import TutorialPage from "@/app/tutorial/page";

describe("tutorial flow", () => {
  test("renders an interactive commercial demo path", () => {
    render(<TutorialPage />);

    expect(screen.getByRole("heading", { name: "Tutorial" })).toBeInTheDocument();
    expect(screen.getByText("PR/CI adapter")).toBeInTheDocument();
    expect(screen.getByText(/Let enterprises connect agents to CI\/CD/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Pilot Dataset/).length).toBeGreaterThan(0);
    expect(screen.getByText("High-risk generated PR")).toBeInTheDocument();
    expect(screen.getByText("Pilot Control Console")).toBeInTheDocument();
    expect(screen.getByText("0/5 scenario gates completed")).toBeInTheDocument();
    expect(screen.getByText(/Buyer review status: Not ready/)).toBeInTheDocument();
    expect(screen.queryByText(/Run all/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run Next Scenario" })).toHaveAttribute(
      "href",
      "/orchestrate?scenario=high-risk-generated-pr"
    );
    expect(screen.getAllByRole("link", { name: "Run Scenario" })[0]).toHaveAttribute(
      "href",
      "/orchestrate?scenario=high-risk-generated-pr"
    );
    expect(screen.getByText(/first run should block until approval is confirmed/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Verify evidence/ }));

    expect(screen.getByText("audit report")).toBeInTheDocument();
    expect(screen.getByText("Policy gate decision")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare Plans" })).toHaveAttribute("href", "/monetization");
  });
});
