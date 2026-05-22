import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AppNav } from "@/components/layout/AppNav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/monetization",
}));

describe("app nav", () => {
  test("renders categorized navigation for commercial MVP surfaces", () => {
    render(<AppNav />);

    expect(screen.getByText("Operate")).toBeInTheDocument();
    expect(screen.getByText("Commercial")).toBeInTheDocument();
    expect(screen.getByText("Learn")).toBeInTheDocument();
    expect(screen.getByText("Assets")).toBeInTheDocument();
    expect(screen.getByText("Personal Loops")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Plans & Usage" })).toHaveClass("nav-link-active");
  });
});
