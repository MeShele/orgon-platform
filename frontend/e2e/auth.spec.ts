import { test, expect } from "@playwright/test";

// Authenticated flow — relies on the demo seed (migration 013).
// Skipped automatically when no E2E_BACKEND_URL is set; the smoke tests
// can run without a backend, this one cannot.

const BACKEND = process.env.E2E_BACKEND_URL;
test.skip(!BACKEND, "E2E_BACKEND_URL not set — skipping authenticated flow.");

test("demo-admin can log in and reach the dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("demo-admin@orgon.io");
  await page.getByLabel(/пароль|password/i).fill("demo2026");
  await page.getByRole("button", { name: /войти|login/i }).click();

  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
  // Sidebar should expose at least a few authenticated links.
  await expect(page.getByRole("link", { name: /wallets/i })).toBeVisible();
});
