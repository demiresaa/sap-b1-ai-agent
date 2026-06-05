/**
 * Smoke E2E — login → pipeline.
 *
 * Backend ve frontend ayağa kalkmış olmalı. `seed.py` çalışmış olmalı:
 *   admin@example.com / admin123
 */
import { expect, test } from "@playwright/test";

const TEST_EMAIL = process.env.TEST_USER_EMAIL ?? "admin@example.com";
const TEST_PASSWORD = process.env.TEST_USER_PASSWORD ?? "admin123";

test("login → pipeline'a geçiş", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "SAP B1 AI Agent" })).toBeVisible();

  await page.getByLabel("E-posta").fill(TEST_EMAIL);
  await page.getByLabel("Şifre").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Giriş Yap" }).click();

  await page.waitForURL("**/pipeline", { timeout: 10_000 });
  await expect(page.getByRole("heading", { name: "Pipeline" })).toBeVisible();
  await expect(page.getByText("Gelen")).toBeVisible();
  await expect(page.getByText("SAP'a Yazıldı")).toBeVisible();
});

test("yanlış parola Türkçe hata gösterir", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-posta").fill(TEST_EMAIL);
  await page.getByLabel("Şifre").fill("yanlis-parola");
  await page.getByRole("button", { name: "Giriş Yap" }).click();

  await expect(page.getByText(/hatalı/i)).toBeVisible();
});

test("auth olmadan dashboard'a girilemez", async ({ page }) => {
  await page.goto("/pipeline");
  await page.waitForURL("**/login", { timeout: 5_000 });
});
