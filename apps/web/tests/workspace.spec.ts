import { test, expect } from "@playwright/test";
test.skip(process.env.RESEARCHOS_LIVE === "1", "Offline integration suite");
test("source upload, ranked passages, local NLP, citation scope and download", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Research desk" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Source library", exact: true })
    .click();
  await page.getByLabel("Upload documents").setInputFiles({
    name: "browser-study.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "BERT was evaluated on SQuAD. This model uses self-attention.",
    ),
  });
  await expect(page.getByText("1 source is ready.")).toBeVisible();
  await page
    .getByRole("button", { name: "Research desk", exact: true })
    .click();
  await page.getByRole("tab", { name: "Passage search" }).click();
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill("Which dataset evaluated BERT?");
  await page.getByRole("button", { name: "Find passages" }).click();
  await expect(
    page.getByRole("heading", { name: "Retrieved passages" }),
  ).toBeVisible();
  await expect(page.locator("blockquote").first()).toContainText("SQuAD");
  await page
    .getByRole("combobox", { name: "Source", exact: true })
    .selectOption({ label: "browser-study.txt" });
  await page
    .getByRole("button", { name: "Helpful source", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Feedback saved.");
  const saved = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download result as JSON" }).click();
  expect((await saved).suggestedFilename()).toEqual("research-result.json");
  await page.getByRole("button", { name: "Language lab", exact: true }).click();
  await page
    .getByRole("button", { name: "Use first selected document" })
    .click();
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Language analysis" }),
  ).toBeVisible();
  await expect(page.getByLabel("Knowledge graph")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Coreference" }),
  ).toBeVisible();
  await page.getByLabel("Operation").selectOption("extractive");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "extractive term frequency" }),
  ).toBeVisible();
});
test("project settings persist and invalid project IDs are rejected", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Project settings", exact: true })
    .click();
  await page
    .getByLabel("Research preferences")
    .fill("Use short source quotations.");
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByRole("status")).toHaveText("Preferences saved.");
  await page.reload();
  await page
    .getByRole("button", { name: "Project settings", exact: true })
    .click();
  await expect(page.getByLabel("Research preferences")).toHaveValue(
    "Use short source quotations.",
  );
  await page.getByLabel("Project ID").fill("space invalid");
  await page.getByRole("button", { name: "Open project" }).click();
  await expect(page.locator(".error[role=alert]")).toContainText("letters");
});
test("saved custom workflow renders its actual task graph and provider error", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Source library", exact: true })
    .click();
  await page.getByLabel("Upload documents").setInputFiles({
    name: "agency-test.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Brooklyn Bridge opened in 1883."),
  });
  await expect(page.getByText("1 source is ready.")).toBeVisible();
  await page
    .getByRole("button", { name: "Agent workflows", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill("Which year did the bridge open?");
  await page.getByText("Workflow design & budgets").click();
  await page.getByLabel("Strategy").selectOption("custom");
  await page.getByRole("button", { name: "Launch workflow" }).click();
  await expect(
    page.getByRole("heading", { name: "Live workflow" }),
  ).toBeVisible();
  await expect(page.locator(".task-node").first()).toBeVisible();
  await page.locator(".task-node").first().click();
  await expect(
    page
      .locator("p")
      .filter({ hasText: "Find source passages that answer the question." }),
  ).toBeVisible();
  await expect(
    page.locator(".section-title .chip").filter({ hasText: "FAILED" }),
  ).toBeVisible({ timeout: 20000 });
  await page.getByRole("button", { name: "Run history", exact: true }).click();
  await expect(page.locator("button.history").first()).toBeVisible();
});
