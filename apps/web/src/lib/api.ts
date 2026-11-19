export type Source = {
  id: string;
  filename: string;
  pages: { number: number | null; text: string }[];
};
export type Task = {
  id: string;
  agent: string;
  description: string;
  dependencies: string[];
  tools: string[];
  acceptance: string[];
};
export type Finding = {
  summary: string;
  evidence: { chunk_id: string; document_id: string; quote: string }[];
  limitations: string[];
};
export type Run = {
  id: string;
  state: string;
  llm_calls: number;
  tool_calls: number;
  tokens: number;
  elapsed: number;
  error: string | null;
  plan: { tasks: Task[] } | null;
  tasks: Record<string, { state: string }>;
  report: {
    results: Finding[];
    verification: { outcome: string };
    limitations: string[];
  } | null;
};
export type EventRow = {
  span_id?: string;
  sequence: number;
  stage?: string;
  status?: string;
  type?: string;
  state?: string;
  time: number;
  task_id?: string;
  tool?: string;
  http_status?: number;
};
export type Profile = { preferences: string; adaptive_retrieval: boolean };
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api/aura" + path, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      typeof error.error === "string"
        ? error.error
        : typeof error.detail === "string"
          ? error.detail
          : Array.isArray(error.detail)
            ? error.detail.map((d: { msg: string }) => d.msg).join(". ")
            : "Request failed (" + response.status + ")",
    );
  }
  return response.json();
}
export function send<T>(
  path: string,
  body: unknown,
  trace?: string,
  method = "POST",
) {
  return api<T>(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(trace ? { "X-Aura-Trace": trace } : {}),
    },
    body: JSON.stringify(body),
  });
}
export function download(
  name: string,
  contents: string,
  type = "text/markdown",
) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const terminal = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
export function markdown(run: Run) {
  return [
    "# Research report",
    "Status: " + run.state,
    "Verification: " + (run.report?.verification.outcome ?? "Unavailable"),
    ...(run.report?.results ?? []).flatMap((r) => [
      r.summary,
      ...r.evidence.map(
        (e) =>
          "> " + e.quote + "\n\nSource: " + e.document_id + " / " + e.chunk_id,
      ),
      ...r.limitations,
    ]),
    ...(run.report?.limitations ?? []),
  ].join("\n\n");
}

export type Analysis = {
  coreference: { mention: string; antecedent: { text: string } }[];
  tokens: unknown[];
  sentences: string[];
  entities: { text: string; label: string; start: number }[];
  relations: {
    subject: { text: string; label: string };
    predicate: string;
    object: { text: string; label: string };
    evidence: string;
  }[];
  language: { code: string };
  extractive_summary: { text: string };
};
export type Result = {
  review?: { outcome: string; claims?: { claim: string; outcome: string }[] };
  usage?: number;
  title: string;
  text?: string;
  passages?: {
    text: string;
    filename?: string;
    page?: number | null;
    id?: string;
  }[];
  analysis?: Analysis;
  raw: unknown;
};
