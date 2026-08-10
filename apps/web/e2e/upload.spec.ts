import { test, expect } from "@playwright/test";

test.describe("Core navigation", () => {
  test("should display the datasets page", async ({ page }) => {
    await page.goto("/datasets");
    await expect(page).toHaveURL(/datasets/);
  });

  test("should display the raw media (ingest) page", async ({ page }) => {
    await page.goto("/ingest");
    await expect(page).toHaveURL(/ingest/);
  });

  test("should navigate to files page", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });

  test("should display the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });
});
