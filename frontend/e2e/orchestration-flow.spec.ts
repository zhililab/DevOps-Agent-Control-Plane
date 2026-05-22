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
  await expect(page.getByLabel("Apply Existing Template")).toBeVisible();
  await expect(page.getByLabel("Required Tier")).toBeVisible();
  await expect(page.getByLabel("Billable Work Units")).toBeVisible();
  await expect(page.getByText("Loading templates...")).toHaveCount(0);
  await expect(page.getByText("Request timed out. Please retry.")).toHaveCount(0);
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
  await expect(page.getByText("Loading orchestration history...")).toHaveCount(0);
  await expect(page.getByText("Loading queue jobs...")).toHaveCount(0);
  await expect(page.getByText("Request timed out. Please retry.")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: `Run #${runId}` })).toBeVisible();
  const runCard = page.locator(`#orchestration-run-${runId}`);
  await expect(runCard.getByText(/success · pro · \d+ms/)).toBeVisible();
  await expect(runCard.getByText(/Team: platform-team · requested by sre-lead/)).toBeVisible();
  await expect(runCard.getByText(/Checkpoints: [1-9]\d*/)).toBeVisible();
  await expect(runCard.getByText("Plan The Day (planner) - success")).toBeVisible();
  await expect(runCard.getByText("Analyze Technical Signals (analyzer) - success")).toBeVisible();
  await expect(runCard.getByText("Review And Reflect (reviewer) - success")).toBeVisible();

  await runCard.getByRole("button", { name: "Verify History Ledger" }).click();
  await expect(runCard.getByText(/History Ledger: valid · \d+ event\(s\)/)).toBeVisible();
  await expect(runCard.locator(`[aria-label="checkpoint-timeline-${runId}"]`)).toBeVisible();

  await page.reload();
  const reloadedRunCard = page.locator(`#orchestration-run-${runId}`);
  await expect(reloadedRunCard.getByText(/History Ledger: valid · \d+ event\(s\)/)).toBeVisible();
  await expect(reloadedRunCard.getByText(/Checkpoints: [1-9]\d*/)).toBeVisible();
});
