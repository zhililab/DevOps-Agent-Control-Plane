import { render } from "@testing-library/react";
import { vi } from "vitest";

import { RouteTransitionFX } from "@/components/layout/RouteTransitionFX";

let mockedPathname = "/dashboard";

vi.mock("next/navigation", () => ({
  usePathname: () => mockedPathname,
}));

describe("route transition performance guard", () => {
  beforeEach(() => {
    mockedPathname = "/dashboard";
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  test("does not run route animation when reduced motion is requested", () => {
    const { container, rerender } = render(<RouteTransitionFX />);

    mockedPathname = "/monetization";
    rerender(<RouteTransitionFX />);

    expect(container.firstChild).not.toHaveClass("route-transition-active");
  });
});
