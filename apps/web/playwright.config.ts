import { defineConfig } from "@playwright/test";
const python = process.env.RESEARCHOS_TEST_PYTHON || "python3";
export default defineConfig({
  testDir: "tests",
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:13135",
    launchOptions: process.env.RESEARCHOS_CHROME
      ? { executablePath: process.env.RESEARCHOS_CHROME }
      : {},
  },
  webServer: [
    {
      command: python + " tests/api_fixture.py",
      url: "http://127.0.0.1:18135/health",
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 13135 --hostname 127.0.0.1",
      url: "http://127.0.0.1:13135",
      env: {
        AURA_API_ORIGIN: "http://127.0.0.1:18135",
        NEXT_TELEMETRY_DISABLED: "1",
      },
      timeout: 60000,
    },
  ],
});
