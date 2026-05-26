import { expect, test } from "@playwright/test";

test("runs orchestration and verifies replay from history", async ({ page }) => {
  let runHeaders: Record<string, string> | null = null;

  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/orchestrations/run")) {
      runHeaders = request.headers();
    }
  });

  await page.goto("/monetization");
  await expect(page.getByRole("heading", { name: "Plans & Usage" })).toBeVisible();
  const powerButton = page.getByRole("button", { name: /Activate Power|Refresh Plan/ }).last();
  await powerButton.scrollIntoViewIfNeeded();
  await powerButton.click();
  await expect(page.getByText(/POWER subscription is active|POWER · active/).first()).toBeVisible();

  await page.goto("/tutorial");
  await expect(page.getByRole("heading", { name: "Tutorial" })).toBeVisible();
  await page.getByRole("link", { name: /High-risk generated PR/ }).click();

  await expect(page).toHaveURL(/\/orchestrate\?scenario=high-risk-generated-pr/);
  await expect(page.getByRole("heading", { name: "Workflow Orchestrator" })).toBeVisible();
  await expect(page.getByText("Pilot Scenario Pack V2")).toBeVisible();
  await expect(page.getByText("Loaded pilot scenario: High-risk generated PR.")).toBeVisible();
  await expect(page.getByLabel("Apply Existing Template")).toBeVisible();
  await expect(page.getByLabel("Required Tier")).toBeVisible();
  await expect(page.getByLabel("Billable Work Units")).toBeVisible();
  await expect(page.getByText(/Power-gated release evidence|Power-gated/i)).toBeVisible();
  await expect(page.getByText("Loading templates...")).toHaveCount(0);
  await expect(page.getByText("Request timed out. Please retry.")).toHaveCount(0);
  await page.getByRole("button", { name: "Load Subscription Entitlement" }).click();
  await expect(page.getByText(/POWER subscription entitlement loaded|Current entitlement: POWER/).first()).toBeVisible();
  await page.getByLabel("Entry Source").fill(`e2e_pilot_${Date.now()}`);
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

  await expect(page.getByText("Normalize PR Change Request (planner) - success")).toBeVisible();
  await expect(page.getByText("Evaluate CI And Deployment Risk (analyzer) - success")).toBeVisible();
  await expect(page.getByText("Decide PR Release Gate (reviewer) - success")).toBeVisible();

  await page.getByRole("link", { name: "View Orchestration History" }).click();

  await expect(page).toHaveURL(/\/orchestrations$/);
  await expect(page.getByRole("heading", { name: "Orchestration History" })).toBeVisible();
  await expect(page.getByText("Loading orchestration history...")).toHaveCount(0);
  await expect(page.getByText("Loading queue jobs...")).toHaveCount(0);
  await expect(page.getByText("Request timed out. Please retry.")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: `Run #${runId}` })).toBeVisible();
  const runCard = page.locator(`#orchestration-run-${runId}`);
  await expect(runCard.getByText(/success · power · \d+ms/)).toBeVisible();
  await expect(runCard.getByText(/Team: platform-team · requested by sre-lead/)).toBeVisible();
  await expect(runCard.getByText("Audit Report")).toBeVisible();
  await expect(runCard.getByText(/Policy Gate/)).toBeVisible();
  await expect(runCard.getByText(/Billable Work Units/)).toBeVisible();
  await expect(runCard.getByText(/Blocked Risk/)).toBeVisible();
  await expect(runCard.getByText(/Checkpoints: [1-9]\d*/)).toBeVisible();
  await expect(runCard.getByText("Normalize PR Change Request (planner) - success")).toBeVisible();
  await expect(runCard.getByText("Evaluate CI And Deployment Risk (analyzer) - success")).toBeVisible();
  await expect(runCard.getByText("Decide PR Release Gate (reviewer) - success")).toBeVisible();

  await runCard.getByRole("button", { name: "Verify History Ledger" }).click();
  await expect(runCard.getByText(/History Ledger: valid · \d+ event\(s\)/)).toBeVisible();
  await expect(runCard.locator(`[aria-label="checkpoint-timeline-${runId}"]`)).toBeVisible();
  await runCard.getByRole("button", { name: "Export Evidence" }).click();
  await expect(runCard.getByRole("heading", { name: "Evidence Export" })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await runCard.getByRole("button", { name: "Download Markdown" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(`orchestration-${runId}-evidence.md`);

  await page.goto("/monetization");
  await expect(page.getByText("Commercial Signal")).toBeVisible();
  await expect(page.getByText("Pilot Readiness")).toBeVisible();
  await expect(page.getByText(/Estimated Pilot Value|Pilot Readiness/).first()).toBeVisible();

  await page.goto("/dashboard");
  await expect(page.getByText("Pilot Ready")).toBeVisible();
  await expect(page.getByText("Estimated Value")).toBeVisible();

  await page.reload();
  await page.goto("/orchestrations");
  const reloadedRunCard = page.locator(`#orchestration-run-${runId}`);
  await expect(reloadedRunCard.getByText(/History Ledger: valid · \d+ event\(s\)/)).toBeVisible();
  await expect(reloadedRunCard.getByText(/Checkpoints: [1-9]\d*/)).toBeVisible();
});
