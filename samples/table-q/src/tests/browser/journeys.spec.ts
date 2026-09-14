import { test, expect } from "@playwright/test";
import { seed } from "../../server/seed";
import { pool, one } from "../../server/db";
import { digest, uid, token } from "../../server/security";
import { cleanupAccount } from "../cleanup";
let email: string, password: string, account: string;
test.beforeAll(async () => {
  email = "browser-" + uid() + "@tableq.local";
  password = token();
  process.env.SEED_EMAIL = email;
  process.env.SEED_PASSWORD = password;
  process.env.SEED_PREFIX = uid().slice(0, 8) + "-";
  await seed();
  account = (
    await one(
      pool,
      "SELECT account_id FROM operator_accounts WHERE login_digest=$1",
      [digest("login", email)],
    )
  ).account_id;
});
test.afterAll(async () => {
  if (account) await cleanupAccount(account);
  await pool.end();
});
test("head office, tablet, read-only watch, offline reload/reconnect and manager layout", async ({
  page,
  context,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in →" }).click();
  await expect(
    page.getByRole("heading", { name: "The bigger picture." }),
  ).toBeVisible();
  await page.screenshot({ path: "data/head-office.png", fullPage: true });
  await page.getByRole("link", { name: "Manage →" }).first().click();
  await page.getByRole("button", { name: "Open store tablet ↗" }).click();
  await page.getByLabel("Store PIN").fill("246810");
  await page.getByRole("button", { name: "Unlock", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Keep things moving." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add group", exact: true }).click();
  await page
    .getByRole("button", { name: "Add to queue and issue watch code" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your place is saved." }),
  ).toBeVisible();
  const code = (await page.locator(".watch-code").innerText()).replaceAll(
    " ",
    "",
  );
  await page.getByRole("button", { name: "Back to queue" }).click();
  await expect(page.locator(".queue-row")).toHaveCount(1);
  const tabletURL = page.url();
  const customer = await context.newPage();
  await customer.setViewportSize({ width: 390, height: 844 });
  await customer.goto("/w");
  for (const digit of code)
    await customer.getByRole("button", { name: digit, exact: true }).click();
  await customer.getByRole("button", { name: "Watch my queue →" }).click();
  await expect(
    customer.getByText("Groups ahead of you", { exact: false }),
  ).toBeVisible();
  await expect(
    customer.getByRole("button", { name: "Leave the queue" }),
  ).toHaveCount(0);
  await customer.screenshot({
    path: "data/customer-watch.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Simulate connection loss" }).click();
  await page.getByRole("button", { name: "Call next eligible →" }).click();
  await expect(page.locator(".queue-row.called")).toHaveCount(1);
  await page.getByRole("button", { name: "Seat", exact: true }).click();
  await page.getByRole("button", { name: "Tables", exact: true }).click();
  await page.getByRole("button", { name: "Clear table", exact: true }).click();
  await page.reload();
  await expect(
    page.getByText("3 actions pending", { exact: false }),
  ).toBeVisible();
  await page.screenshot({ path: "data/tablet-offline.png", fullPage: true });
  await page.getByRole("button", { name: "Reconnect store" }).click();
  await expect(page.getByText("actions pending", { exact: false })).toHaveCount(
    0,
    { timeout: 45000 },
  );
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.screenshot({ path: "data/tablet-online.png", fullPage: true });
  await customer.close();
  await page.goto(tabletURL.replace("/tablet/", "/settings/"));
  await page.getByRole("button", { name: "Layout", exact: true }).click();
  await expect(page.locator(".dining")).toHaveCount(12);
  await page.screenshot({ path: "data/manager-layout.png", fullPage: true });
  expect(errors).toEqual([]);
});
test("customer store search and kiosk check-in use responsive screens", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/stores");
  await page.getByLabel("Search restaurants").fill("Gangnam");
  await expect(page.locator(".store-card").first()).toBeVisible();
  await page.screenshot({ path: "data/customer-search.png", fullPage: true });
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in →" }).click();
  await page.getByRole("link", { name: "Manage →" }).first().click();
  await page.getByRole("button", { name: "Open kiosk ↗" }).click();
  await page.getByRole("button", { name: "Check in — 2 people →" }).click();
  await expect(
    page.getByRole("heading", { name: "You’re on the list." }),
  ).toBeVisible();
  await expect(page.locator(".watch-code")).toHaveText(/\d{4}/);
  await page.screenshot({ path: "data/kiosk.png", fullPage: true });
});
test("installed app reloads and operates with the browser network physically offline", async ({
  page,
  context,
}) => {
  await page.goto("http://127.0.0.1:3100/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in →" }).click();
  await page.getByRole("link", { name: "Manage →" }).last().click();
  await page.getByRole("button", { name: "Open store tablet ↗" }).click();
  await page.getByLabel("Store PIN").fill("246810");
  await page.getByRole("button", { name: "Unlock", exact: true }).click();
  await page.getByRole("button", { name: "Add group", exact: true }).click();
  await page
    .getByRole("button", { name: "Add to queue and issue watch code" })
    .click();
  await page.getByRole("button", { name: "Back to queue" }).click();
  await expect(page.locator(".queue-row")).toHaveCount(1);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Keep things moving." }),
  ).toBeVisible();
  await context.setOffline(true);
  console.log(
    "offline before reload",
    await page.evaluate(() => ({
      online: navigator.onLine,
      saved: sessionStorage.getItem("tablet-offline"),
    })),
  );
  await page.reload();
  console.log(
    "offline after reload",
    await page.evaluate(() => ({
      online: navigator.onLine,
      saved: sessionStorage.getItem("tablet-offline"),
    })),
  );
  await expect(
    page.getByRole("button", { name: "Reconnect store" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Call next eligible →" }).click();
  await page.getByRole("button", { name: "Seat", exact: true }).click();
  await page.getByRole("button", { name: "Tables", exact: true }).click();
  await page.getByRole("button", { name: "Clear table", exact: true }).click();
  await expect(
    page.getByText("3 actions pending", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "data/tablet-real-offline.png",
    fullPage: true,
  });
  await context.setOffline(false);
  await expect(page.getByText("actions pending", { exact: false })).toHaveCount(
    0,
    { timeout: 45000 },
  );
  await expect(page.getByRole("alert")).toHaveCount(0);
});
