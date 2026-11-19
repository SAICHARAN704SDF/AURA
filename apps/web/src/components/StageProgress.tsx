import type { EventRow } from "../lib/api";
import { CheckCircle2, CircleAlert, CircleDot, Hourglass } from "lucide-react";

const groups: {
  name: string;
  steps: [string, string, string][];
}[] = [
  {
    name: "Document preparation",
    steps: [
      [
        "parsing",
        "Read the source",
        "Extract text while preserving the source page.",
      ],
      [
        "ocr",
        "Read scanned pages",
        "Recognize text on image-only pages when OCR is needed.",
      ],
      [
        "chunking",
        "Split into passages",
        "Keep page and character positions with each passage.",
      ],
      [
        "embeddings",
        "Represent meaning",
        "Convert text into vectors or reuse cached vectors.",
      ],
      [
        "vector_storage",
        "Index passages",
        "Store the searchable passages with their source references.",
      ],
    ],
  },
  {
    name: "Language processing",
    steps: [
      [
        "spacy_pipeline",
        "Read the language",
        "Tokenize the text and apply the loaded spaCy language pipeline.",
      ],
      [
        "text_preprocessing",
        "Normalize terms",
        "Clean and normalize terms for counting.",
      ],
      [
        "relation_extraction",
        "Find relationships",
        "Connect matching entities using evidence in their sentence.",
      ],
      [
        "extractive_summary",
        "Select sentences",
        "Rank and return representative source sentences.",
      ],
      [
        "cosine_similarity",
        "Compare meaning",
        "Measure the angle between the two passage vectors.",
      ],
    ],
  },
  {
    name: "Evidence and generation",
    steps: [
      ["dense_search", "Search by meaning", "Retrieve nearby passage vectors."],
      [
        "lexical_search",
        "Search by words",
        "Rank passages using matching terms.",
      ],
      [
        "context_assembly",
        "Prepare evidence",
        "Package selected passages for the language model.",
      ],
      [
        "answer_generation",
        "Generate the answer",
        "Ask the configured model to answer from the evidence.",
      ],
      [
        "citation_validation",
        "Check quotations",
        "Compare each citation with the referenced source passage.",
      ],
      [
        "claim_review",
        "Review claims",
        "Review the support for individual claims.",
      ],
    ],
  },
  {
    name: "Agent coordination",
    steps: [
      [
        "planning",
        "Plan tasks",
        "Build or load a validated graph of tasks and dependencies.",
      ],
      [
        "task_wave",
        "Run ready tasks",
        "Dispatch eligible tasks within the run budgets.",
      ],
      [
        "workflow_checkpoint",
        "Save progress",
        "Persist workflow state for inspection and recovery.",
      ],
      [
        "verification",
        "Verify the report",
        "Review the outputs and store the verified or partial result.",
      ],
    ],
  },
];
export default function StageProgress({ rows }: { rows: EventRow[] }) {
  const visible = groups
    .map((group) => ({
      ...group,
      steps: group.steps.map(([key, label, hint]) => {
        const events = rows.filter((e) => e.stage === key);
        if (!events.length) return null;
        const active = new Set<string | number>();
        let failures = 0;
        for (const event of events) {
          const id = event.span_id ?? key;
          if (event.status === "started") active.add(id);
          if (["failed", "completed", "cancelled"].includes(event.status ?? ""))
            active.delete(id);
          if (event.status === "failed") failures++;
        }
        const status = active.size
          ? "Running"
          : failures
            ? "Observed failure"
            : events.some((e) => e.status === "completed")
              ? "Completed"
              : "Observed";
        return { key, label, hint, status, count: events.length };
      }),
    }))
    .filter((g) => g.steps.some(Boolean));
  if (!visible.length) return null;
  return (
    <div className="stage-groups">
      {visible.map((g) => (
        <details key={g.name} open>
          <summary>{g.name}</summary>
          <div className="stage-grid">
            {g.steps.map((step) => {
              if (!step) return null;
              const Icon =
                step.status === "Running"
                  ? Hourglass
                  : step.status === "Observed failure"
                    ? CircleAlert
                    : step.status === "Completed"
                      ? CheckCircle2
                      : CircleDot;
              return (
                <details key={step.key} className="stage-card">
                  <summary>
                    <Icon size={15} />
                    <strong>{step.label}</strong>
                    <small>{step.status}</small>
                  </summary>
                  <p>{step.hint}</p>
                  <small>{step.count} recorded events</small>
                </details>
              );
            })}
          </div>
        </details>
      ))}
    </div>
  );
}
