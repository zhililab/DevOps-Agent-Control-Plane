import { expect, test } from "@playwright/test";

test("activates a commercial plan and shows usage plus scoped audit feed", async ({ page }) => {
  const subject = `e2e-commercial-${Date.now()}`;

  await page.goto("/monetization");

  await expect(page.getByRole("heading", { name: "Plans & Usage" })).toBeVisible();
  await expect(page.getByText("Turn trusted DevOps runs into metered plans.")).toBeVisible();

  await page.getByLabel("Account Subject").fill(subject);
  await page.getByRole("button", { name: "Load Account" }).click();
  await expect(page.getByText("No subscription profile")).toBeVisible();

  await page.getByRole("button", { name: "Activate Pro" }).click();

  await expect(page.getByText("PRO subscription is active.")).toBeVisible();
  await expect(page.getByText(/PRO · active/).first()).toBeVisible();
  await expect(page.getByText("Workflow Runs", { exact: true })).toBeVisible();
  await expect(page.getByText("0 / 300").first()).toBeVisible();
  await expect(page.getByText("Commercial Audit Feed")).toBeVisible();
  await expect(page.getByText("checkout completed")).toBeVisible();
  await expect(page.getByText("Request timed out. Please retry.")).toHaveCount(0);
});
