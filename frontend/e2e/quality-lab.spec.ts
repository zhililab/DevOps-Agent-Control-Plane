import { expect, test } from "@playwright/test";


test("builds reproducible quality and measured pilot evidence", async ({ page }) => {
  await page.goto("/evaluation");

  await expect(page.getByRole("heading", { name: "Agent Quality Lab" })).toBeVisible();
  await expect(page.getByText("pr-ci-gate.v1.25 · 25 versioned cases")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Live Model" })).toBeDisabled();

  await page.getByRole("button", { name: "Run Rules Baseline" }).click();
  await expect(page.getByText("Deterministic evaluation completed.")).toBeVisible();
  await expect(page.getByText("25/25 exact decisions")).toBeVisible();

  const firstResult = page.locator(".quality-result-row").first();
  await expect(firstResult.getByText("match", { exact: true })).toBeVisible();
  await firstResult.getByRole("button", { name: "Accept" }).click();
  await expect(page.getByText("Human decision feedback recorded as an append-only review event.")).toBeVisible();
  const feedbackPanel = page.locator('[aria-label="human-feedback"]');
  await expect(feedbackPanel.locator(".kpi-card").filter({ hasText: "Reviewed" }).getByText("1", { exact: true })).toBeVisible();

  const measurementPanel = page.locator('[aria-label="pilot-measurement"]');
  await measurementPanel.getByLabel("Account").fill("e2e-quality-user");
  await measurementPanel.getByLabel("Team").fill("e2e-quality-team");
  await measurementPanel.getByLabel("Metric").selectOption("review_minutes");
  await measurementPanel.getByLabel("Phase").selectOption("baseline");
  await measurementPanel.getByLabel("Observed value").fill("30");
  await measurementPanel.getByLabel("Sample size").fill("2");
  await measurementPanel.getByRole("button", { name: "Save Observation" }).click();
  await expect(page.getByText("baseline measurement saved; estimated ROI remains separately labeled.")).toBeVisible();

  await measurementPanel.getByLabel("Phase").selectOption("pilot");
  await measurementPanel.getByLabel("Observed value").fill("12");
  await measurementPanel.getByRole("button", { name: "Save Observation" }).click();
  await expect(page.getByText("pilot measurement saved; estimated ROI remains separately labeled.")).toBeVisible();
  await expect(measurementPanel.getByText("30 → 12")).toBeVisible();
  await expect(measurementPanel.getByText("60% improvement · minutes")).toBeVisible();
});
