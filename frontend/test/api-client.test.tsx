import { afterEach, describe, expect, test, vi } from "vitest";

describe("api client base URL", () => {
  const originalApiBase = process.env.NEXT_PUBLIC_API_BASE;

  afterEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    if (originalApiBase === undefined) {
      delete process.env.NEXT_PUBLIC_API_BASE;
    } else {
      process.env.NEXT_PUBLIC_API_BASE = originalApiBase;
    }
  });

  test("defaults browser requests to the same-origin API proxy", async () => {
    vi.resetModules();
    delete process.env.NEXT_PUBLIC_API_BASE;
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ items: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { apiClient } = await import("@/lib/api");

    await apiClient.listDailyPlans();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/plans/history",
      expect.objectContaining({
        cache: "no-store",
      })
    );
    expect(fetchMock.mock.calls[0]?.[0]?.toString()).not.toContain("localhost:8000");
  });
});
