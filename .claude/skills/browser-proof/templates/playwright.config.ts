import { defineConfig } from "@playwright/test";

// End-to-end tests run against the application as it is really launched (docker compose, a dev
// server…), not against a build made for the test. Vitest/Jest must not pick this folder up.
export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000, // one long scenario, not many small tests
  expect: { timeout: 10_000 },
  workers: 1, // the scenario writes to a shared database
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    viewport: { width: 1280, height: 900 },
    screenshot: "only-on-failure",
  },
});
