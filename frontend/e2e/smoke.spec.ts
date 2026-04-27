import { test, expect } from "@playwright/test";

// Smoke tests — validate that the public surface renders without
// requiring a live backend. Authenticated flows live in auth.spec.ts.

test("landing page renders the Crimson Ledger hero", async ({ page }) => {
  await page.goto("/");
  // Hero headline (Russian copy) — single source-of-truth string.
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    /Multi-signature/i,
  );
  // Demo CTA mailto — sanity check it didn't drift back to /contact.
  const demoCta = page.getByRole("link", { name: /демо/i }).first();
  await expect(demoCta).toHaveAttribute("href", /^mailto:sales@/);
});

test("login page is reachable and form fields exist", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await expect(page.getByLabel(/пароль|password/i)).toBeVisible();
});

test("pricing page lists plan cards", async ({ page }) => {
  await page.goto("/pricing");
  // We have at least 3 tiers (Pilot / Growth / Enterprise — names vary).
  const cards = page.locator("article, section").filter({ hasText: /\$|month|год/i });
  await expect(cards.first()).toBeVisible();
});
