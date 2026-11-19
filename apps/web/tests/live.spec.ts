import { test, expect } from "@playwright/test";
test.skip(
  process.env.RESEARCHOS_LIVE !== "1",
  "Uses the configured embedding, reranker and generation accounts.",
);
test("live providers index a source and return a supported cited answer in Chrome", async ({
  page,
}) => {
  test.setTimeout(145000);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Source library", exact: true })
    .click();
  await page
    .getByLabel("Upload documents")
    .setInputFiles({
      name: "researchos-browser-check.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "The field team recorded fourteen kestrels at North Marsh during the April survey. The team counted each bird once.",
      ),
    });
  await expect(page.getByText("1 source is ready.")).toBeVisible({
    timeout: 65000,
  });
  await page
    .getByRole("button", { name: "Research desk", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill("How many kestrels did the field team record at North Marsh?");
  await page.getByRole("button", { name: "Get answer", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Cited answer", exact: true }),
  ).toBeVisible({ timeout: 65000 });
  await expect(page.locator(".prose")).toContainText(/14|fourteen/i);
  await expect(page.locator("blockquote").first()).toContainText(/kestrels/i);
  await expect(page.locator(".journal")).toContainText("retrieval");
});
test("live collaborative workflow returns a reviewed report and exports Markdown", async ({
  page,
}) => {
  test.setTimeout(210000);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Source library", exact: true })
    .click();
  await page
    .getByLabel("Upload documents")
    .setInputFiles({
      name: "field-observations.md",
      mimeType: "text/markdown",
      buffer: Buffer.from(
        "North Marsh field survey. On April 3 the team counted fourteen kestrels. Observers watched for two hours from a fixed hide. The observers could not estimate how many kestrels flew behind the trees. This single morning survey cannot establish a population trend.",
      ),
    });
  await expect(page.getByText("1 source is ready.")).toBeVisible({
    timeout: 60000,
  });
  await page
    .getByRole("button", { name: "Agent workflows", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill(
      "Write a short report on the kestrel count, the observation method and one limitation. Quote evidence.",
    );
  await page.getByText("Workflow design & budgets").click();
  await page.getByLabel("Strategy").selectOption("collaborative");
  await page.getByRole("button", { name: "Launch workflow" }).click();
  await expect(page.locator(".task-node").first()).toBeVisible({
    timeout: 15000,
  });
  await expect(
    page.getByRole("heading", { name: "Research report", exact: true }),
  ).toBeVisible({ timeout: 150000 });
  await expect(
    page.locator(".section-title .chip").filter({ hasText: "COMPLETED" }),
  ).toBeVisible();
  const report = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download report", exact: true })
    .click();
  expect((await report).suggestedFilename()).toBe("research-report.md");
});
