import { expect, test } from "@playwright/test";

test("runs orchestration and verifies replay from history", async ({ page }) => {
  let runHeaders: Record<string, string> | null = null;

  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/orchestrations/run")) {
      runHeaders = request.headers();
    }
  });

  await page.goto("/orchestrate");

  await expect(page.getByRole("heading", { name: "Workflow Orchestrator" })).toBeVisible();
  await page.getByLabel("Entry Source").fill(`e2e_browser_${Date.now()}`);
  await page.getByLabel("Tasks (one per line)").fill("Validate browser orchestration flow");
  await page.getByLabel("Priorities (one per line)").fill("Validate browser orchestration flow");
  await page.getByLabel("Persist To Knowledge").uncheck();

  await page.getByRole("button", { name: "Run Orchestration" }).click();

  await expect(page.getByRole("heading", { name: "Run Replay" })).toBeVisible();
  const replaySummary = page.locator("section.reflection-section").filter({ hasText: "Run Replay" });
  const runLine = replaySummary.getByText(/Run #\d+.*status=/).first();
  await expect(runLine).toBeVisible();

  const runText = (await runLine.textContent()) ?? "";
  const runId = runText.match(/Run #(\d+)/)?.[1];
  expect(runId).toBeTruthy();
  expect(runHeaders?.["x-entitlement"]).toBeTruthy();
  expect(runHeaders?.["x-subscription-tier"]).toBeUndefined();

  await expect(page.getByText("Plan The Day (planner) - success")).toBeVisible();
  await expect(page.getByText("Analyze Technical Signals (analyzer) - success")).toBeVisible();
  await expect(page.getByText("Review And Reflect (reviewer) - success")).toBeVisible();

  await page.getByRole("link", { name: "View Orchestration History" }).click();

  await expect(page).toHaveURL(/\/orchestrations$/);
  await expect(page.getByRole("heading", { name: "Orchestration History" })).toBeVisible();
  await expect(page.getByRole("heading", { name: `Run #${runId}` })).toBeVisible();
  await expect(page.getByText(/success · pro · \d+ms/).first()).toBeVisible();
  await expect(page.getByText("Plan The Day (planner) - success")).toBeVisible();
  await expect(page.getByText("Analyze Technical Signals (analyzer) - success")).toBeVisible();
  await expect(page.getByText("Review And Reflect (reviewer) - success")).toBeVisible();
});
