"use client";
import { useEffect, useRef, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import * as Tabs from "@radix-ui/react-tabs";
import {
  Activity,
  BookOpen,
  Boxes,
  Check,
  ChevronRight,
  ClipboardList,
  Database,
  Download,
  FileText,
  Folder,
  GitBranch,
  Layers,
  Link as LinkIcon,
  Plus,
  ScanText,
  Search,
  Settings2,
  SlidersHorizontal,
  Square,
  ThumbsDown,
  ThumbsUp,
  Upload,
} from "lucide-react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import {
  api,
  download,
  markdown,
  send,
  terminal,
  type EventRow,
  type Analysis,
  type Result,
  type Run,
  type Source,
  type Task,
} from "../lib/api";
import Workflow from "./Workflow";
import { Button } from "./ui/button";
import Results from "./Results";
import StageProgress from "./StageProgress";
import Settings from "./Settings";
import { Section, ErrorLine, Journal, names } from "./Panels";
import dynamic from "next/dynamic";
import { motion, useReducedMotion } from "motion/react";
const PlanEditor = dynamic(() => import("./PlanEditor"), { ssr: false });
const ModelBenchmarks = dynamic(() => import("./ModelBenchmarks"), {
  ssr: false,
});

type Mode =
  | "answer"
  | "search"
  | "workflow"
  | "language"
  | "library"
  | "history"
  | "settings";
type Job = {
  id: string;
  status: string;
  trace_id?: string;
  retryable?: boolean;
  error?: string;
  document_id?: string;
};
type Trace = { id: string; events: EventRow[]; warning?: string };
const nav = [
  { id: "answer", label: "Research desk", icon: BookOpen },
  { id: "library", label: "Source library", icon: Folder },
  { id: "language", label: "Language lab", icon: ScanText },
  { id: "workflow", label: "Agent workflows", icon: GitBranch },
  { id: "history", label: "Run history", icon: Activity },
  { id: "settings", label: "Project settings", icon: Settings2 },
] as const;
const modes: Record<Mode, [string, string]> = {
  answer: [
    "Research desk",
    "Ask a question and inspect the passages behind the answer.",
  ],
  search: ["Research desk", "Find matching passages in your research library."],
  library: [
    "Source library",
    "Upload documents or import a public source to index its passages.",
  ],
  language: [
    "Language lab",
    "Inspect the words, entities and relationships in a passage.",
  ],
  workflow: [
    "Agent workflows",
    "Plan research tasks and watch the agents gather and verify evidence.",
  ],
  history: [
    "Run history",
    "Open a saved research run to inspect its tasks, evidence and results.",
  ],
  settings: [
    "Project settings",
    "Set project preferences and choose how feedback influences retrieval.",
  ],
};
const projectSchema = z.string().regex(/^[A-Za-z0-9_-]{1,64}$/);
const defaultPlan = JSON.stringify(
  {
    tasks: [
      {
        id: "research",
        agent: "research",
        description: "Find source passages that answer the question.",
        dependencies: [],
        tools: ["rag_search"],
        acceptance: ["Include exact evidence quotations."],
      },
      {
        id: "write",
        agent: "reporting",
        description: "Write a cited report from the research findings.",
        dependencies: ["research"],
        tools: [],
        acceptance: ["Use only supported findings."],
      },
    ],
  },
  null,
  2,
);
function Console() {
  const cache = useQueryClient();
  const [mode, setMode] = useState<Mode>("answer");
  const [project, setProject] = useState("aura_papers");
  const [selected, setSelected] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [runId, setRunId] = useState("");
  const [node, setNode] = useState<Task | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [strategy, setStrategy] = useState("auto");
  const [custom, setCustom] = useState(defaultPlan);
  const [budget, setBudget] = useState(12);
  const [allowSearch, setAllowSearch] = useState(false);
  const [languageOp, setLanguageOp] = useState("analyze");
  const [source, setSource] = useState("");
  const [chunk, setChunk] = useState("recursive");
  const [feedbackSource, setFeedbackSource] = useState("");
  const [feedbackSection, setFeedbackSection] = useState("Report");
  const { register, handleSubmit, getValues, setValue, control } = useForm({
    defaultValues: { question: "", passage: "", second: "" },
  });
  const passage = useWatch({ control, name: "passage" });
  const reduced = useReducedMotion();
  const [ingestion, setIngestion] = useState<Job | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const docs = useQuery({
    queryKey: ["docs"],
    queryFn: () => api<Source[]>("/documents"),
  });
  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => api<{ provider: string; model: string }>("/monitor/status"),
    refetchInterval: 60000,
  });
  const history = useQuery({
    queryKey: ["history", project],
    queryFn: () =>
      api<{ id: string; state: string; updated: number }[]>(
        "/monitor/workflows?project_id=" + project,
      ),
    refetchInterval: mode === "history" ? 5000 : false,
  });
  const run = useQuery({
    queryKey: ["run", project, runId],
    queryFn: () => api<Run>("/workflows/" + runId + "?project_id=" + project),
    enabled: !!runId,
    refetchInterval: (q) =>
      q.state.data && terminal.has(q.state.data.state) ? false : 1000,
  });
  const journal = useQuery({
    queryKey: ["journal", project, runId],
    queryFn: () =>
      api<{ events: EventRow[] }>(
        "/workflows/" + runId + "/events?project_id=" + project,
      ),
    enabled: !!runId,
    refetchInterval: run.data && terminal.has(run.data.state) ? false : 1500,
  });
  const traceId = trace?.id;
  useEffect(() => {
    if (!traceId) return;
    const stream = new EventSource(
      "/api/aura/monitor/stream?trace_id=" + encodeURIComponent(traceId),
    );
    stream.onmessage = (e) => {
      try {
        const row: EventRow = JSON.parse(e.data);
        if (!row.stage) return;
        setTrace((prev) =>
          prev?.id === traceId
            ? {
                id: traceId,
                events: [
                  ...prev.events.filter((r) => r.sequence !== row.sequence),
                  row,
                ].slice(-200),
              }
            : prev,
        );
      } catch {
        /* heartbeat */
      }
    };
    stream.addEventListener("gap", () =>
      setTrace((prev) =>
        prev?.id === traceId
          ? { ...prev, warning: "Older events expired from the live buffer." }
          : prev,
      ),
    );
    stream.onerror = () =>
      setTrace((prev) =>
        prev?.id === traceId
          ? { ...prev, warning: "Reconnecting to the event stream…" }
          : prev,
      );
    return () => stream.close();
  }, [traceId]);
  function choose(next: Mode) {
    setResult(null);
    setMode(next);
    setError(null);
    setNotice("");
  }
  function activate(id: string) {
    setRunId(id);
    setNode(null);
    setTrace({ id, events: [] });
    choose("workflow");
    setResult(null);
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function begin() {
    const id = crypto.randomUUID();
    setTrace({ id, events: [] });
    return id;
  }
  async function followJob(job: Job) {
    setIngestion(job);
    if (job.trace_id) setTrace({ id: job.trace_id, events: [] });
    while (["queued", "running"].includes(job.status)) {
      await new Promise((resolve) => setTimeout(resolve, 850));
      job = await api<Job>("/ingestion/jobs/" + job.id);
      setIngestion(job);
    }
    if (job.status !== "completed" || !job.document_id)
      throw Error(job.error ?? "Ingestion did not complete.");
    const id = job.document_id;
    setSelected((ids) => Array.from(new Set([...ids, id])).slice(-10));
    await cache.invalidateQueries({ queryKey: ["docs"] });
    return id;
  }
  async function ingest(files?: FileList | null) {
    await action(async () => {
      if (!files?.length && !source.trim())
        throw Error("Enter a URL or arXiv identifier.");
      const entries = files?.length ? Array.from(files) : [null];
      const added: string[] = [];
      for (const entry of entries) {
        const traceId = begin();

        let job: Job;
        if (entry) {
          if (entry.size > 5 * 1024 * 1024)
            throw Error(entry.name + " exceeds the 5 MB upload limit.");
          const form = new FormData();
          form.append("file", entry);
          job = await api("/ingestion/jobs/upload?strategy=" + chunk, {
            method: "POST",
            body: form,
            headers: { "X-Aura-Trace": traceId },
          });
        } else
          job = await send(
            "/ingestion/jobs/import",
            { source: source.trim(), strategy: chunk },
            traceId,
          );
        added.push(await followJob(job));
      }
      setNotice(
        added.length +
          " source" +
          (added.length === 1 ? " is" : "s are") +
          " ready.",
      );
      setSource("");
    });
    if (file.current) file.current.value = "";
  }
  async function submit() {
    await action(async () => {
      const { question, passage, second } = getValues();
      const q = question.trim();
      const traceId = begin();
      setResult(null);
      if (mode === "language") {
        const text = passage.trim();
        if (!text) throw Error("Enter a passage to analyze.");
        if (languageOp === "analyze") {
          const analysis = await send<Analysis>(
            "/nlp/analyze",
            { text },
            traceId,
          );
          setResult({ title: "Language analysis", analysis, raw: analysis });
        } else if (languageOp === "similarity") {
          if (!second.trim()) throw Error("Enter both passages.");
          const data = await send<{ cosine: number; model: string }>(
            "/nlp/similarity",
            { first: text, second: second.trim() },
            traceId,
          );
          setResult({
            title: "Semantic similarity",
            text:
              "Cosine similarity: " +
              data.cosine.toFixed(4) +
              " · " +
              data.model,
            raw: data,
          });
        } else {
          const data = await send<{
            text: string;
            method: string;
            evidence: { text: string }[];
          }>(
            "/nlp/summarize",
            { text, mode: languageOp, sentences: 3 },
            traceId,
          );
          setResult({
            title: names(data.method),
            text: data.text,
            passages: data.evidence,
            raw: data,
          });
        }
        return;
      }
      if (!q) throw Error("Enter a research question.");
      if (mode === "workflow") {
        if (!selected.length) throw Error("Select a source for this report.");
        const plan = strategy === "custom" ? JSON.parse(custom) : undefined;
        const goal = await send<{ id: string }>(
          "/goals",
          {
            project_id: project,
            goal: q,
            document_ids: selected,
            strategy: strategy === "custom" ? "auto" : strategy,
            allow_public_search: allowSearch,
            budget: {
              llm_calls: budget,
              tool_calls: 20,
              seconds: 180,
              concurrency: 2,
            },
          },
          traceId,
        );
        const w = await send<{ id: string }>(
          "/workflows",
          { goal_id: goal.id, project_id: project, plan },
          traceId,
        );
        activate(w.id);
        await send("/workflows/" + w.id + "/execute?project_id=" + project, {});
        await cache.invalidateQueries({ queryKey: ["history", project] });
        return;
      }
      if (selected.length > 1 || (mode === "answer" && !selected.length))
        throw Error(
          mode === "answer"
            ? "Select one source for a cited answer."
            : "Select one source or clear the selection to search the library.",
        );
      if (mode === "search") {
        const data = await send<{
          chunks: {
            text: string;
            filename: string;
            page: number | null;
            id: string;
          }[];
        }>(
          "/projects/" + project + "/search",
          { question: q, document_id: selected[0], top_k: 5 },
          traceId,
        );
        setResult({
          title: "Retrieved passages",
          passages: data.chunks,
          raw: data,
        });
      } else {
        const data = await send<{
          usage: number;
          claim_review: Result["review"];
          evidence: { id: string; filename: string; page: number | null }[];
          answer: {
            answer: string;
            citations: { quote: string; chunk_id: string }[];
          };
        }>("/rag/query", { question: q, document_id: selected[0] }, traceId);
        setResult({
          title: "Cited answer",
          review: data.claim_review,
          usage: data.usage,
          text: data.answer.answer,
          passages: data.answer.citations.map((c) => ({
            ...data.evidence.find((p) => p.id === c.chunk_id),
            text: c.quote,
            id: c.chunk_id,
          })),
          raw: data,
        });
      }
    });
  }
  function switchProject(value: string) {
    if (!projectSchema.safeParse(value).success)
      throw Error("Use 1–64 letters, digits, hyphens or underscores.");
    setProject(value);
    setRunId("");
    setTrace(null);
    setResult(null);
    setSelected([]);
  }
  const sourcePicker = (library = false) => (
    <div className="sources">
      {(docs.data ?? [])
        .filter(
          (d) =>
            !library || d.filename.toLowerCase().includes(filter.toLowerCase()),
        )
        .map((d) => (
          <label className="source" key={d.id}>
            <input
              aria-label={"Select " + d.filename}
              checked={selected.includes(d.id)}
              type="checkbox"
              disabled={
                busy || (!selected.includes(d.id) && selected.length >= 10)
              }
              onChange={(e) =>
                setSelected((ids) =>
                  e.target.checked
                    ? [...ids, d.id]
                    : ids.filter((x) => x !== d.id),
                )
              }
            />
            <FileText size={17} />
            <span>{d.filename}</span>
            <small>
              {d.pages.length} {d.pages.length === 1 ? "page" : "pages"}
            </small>
          </label>
        ))}
      {!docs.data?.length && (
        <p className="hint">
          {docs.isPending ? "Loading sources…" : "Your library is empty."}{" "}
          <button className="text-btn" onClick={() => choose("library")}>
            Add a source
          </button>
        </p>
      )}
      <ErrorLine error={docs.error} />
    </div>
  );
  const activeRun = run.data;
  const view = mode === "search" ? "answer" : mode;
  const recent = history.data?.[0];
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="identity">
          <div className="mark">
            <Layers size={23} />
          </div>
          <div>
            <b>ResearchOS</b>
            <small>AURA workspace</small>
          </div>
        </div>
        <p className="side-label">Workspace</p>
        <nav>
          {nav.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={view === id ? "active" : ""}
              disabled={busy}
              onClick={() => choose(id)}
            >
              <Icon size={17} />
              {label}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <span className={"dot " + (status.isSuccess ? "online" : "")} />
          {status.isSuccess
            ? "API connected"
            : status.isError
              ? "API unavailable"
              : "Connecting…"}
        </div>
      </aside>
      <main>
        <header className="crumb">
          <span>
            <Layers size={15} /> Workspace <ChevronRight size={13} />{" "}
            <b>{modes[mode][0]}</b>
          </span>
          <button
            disabled={busy}
            className="project"
            onClick={() => choose("settings")}
          >
            <Folder size={15} />
            {project}
          </button>
        </header>
        <div className="body">
          <div className="heading">
            <motion.div
              key={mode}
              initial={reduced ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18 }}
            >
              <h1>{modes[mode][0]}</h1>
              <p>{modes[mode][1]}</p>
            </motion.div>
            {mode === "library" && (
              <Button disabled={busy} onClick={() => file.current?.click()}>
                <Upload size={16} />
                Upload files
              </Button>
            )}
          </div>
          <input
            hidden
            type="file"
            aria-label="Upload documents"
            ref={file}
            multiple
            accept=".pdf,.txt,.md,.csv,.png,.jpg,.jpeg,.docx,.html,.htm"
            onChange={(e) => void ingest(e.target.files)}
          />
          <ErrorLine error={error} />
          {notice && (
            <p role="status" className="notice">
              <Check size={16} />
              {notice}
            </p>
          )}
          {view === "answer" && (
            <div className="stat-grid">
              {[
                [Database, "Sources", docs.data?.length ?? "—"],
                [
                  GitBranch,
                  "Saved runs",
                  history.data
                    ? history.data.length +
                      (history.data.length === 30 ? "+" : "")
                    : "—",
                ],
                [Boxes, "Generation provider", status.data?.provider ?? "—"],
              ].map(([I, k, v]) => {
                const Icon = I as typeof Database;
                return (
                  <div className="stat" key={String(k)}>
                    <Icon size={18} />
                    <small>{String(k)}</small>
                    <strong>{String(v)}</strong>
                  </div>
                );
              })}
            </div>
          )}
          {["answer", "search", "workflow", "language"].includes(mode) && (
            <div className="columns">
              <div>
                <Section
                  title={
                    mode === "language"
                      ? "Analyze a passage"
                      : mode === "workflow"
                        ? "Research brief"
                        : "Ask your question"
                  }
                >
                  <form onSubmit={handleSubmit(submit)} className="stack">
                    {view === "answer" && (
                      <Tabs.Root
                        value={mode}
                        onValueChange={(v) => {
                          choose(v as Mode);
                          setResult(null);
                        }}
                      >
                        <Tabs.List className="tabs" aria-label="Research mode">
                          <Tabs.Trigger value="answer">
                            Cited answer
                          </Tabs.Trigger>
                          <Tabs.Trigger value="search">
                            Passage search
                          </Tabs.Trigger>
                        </Tabs.List>
                      </Tabs.Root>
                    )}
                    {mode === "language" ? (
                      <>
                        <label>
                          Operation
                          <select
                            value={languageOp}
                            onChange={(e) => {
                              setLanguageOp(e.target.value);
                              setResult(null);
                            }}
                          >
                            {[
                              ["analyze", "Entities & relationships"],
                              ["extractive", "Extractive summary"],
                              ["abstractive", "AI summary"],
                              ["similarity", "Semantic similarity"],
                            ].map(([v, t]) => (
                              <option key={v} value={v}>
                                {t}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Source text
                          <textarea
                            placeholder="Paste a passage from your paper…"
                            maxLength={
                              languageOp === "similarity" ? 2000 : 20000
                            }
                            rows={6}
                            {...register("passage")}
                          />
                        </label>
                        {languageOp === "similarity" && (
                          <label>
                            Second passage
                            <textarea
                              maxLength={2000}
                              {...register("second")}
                            />
                          </label>
                        )}
                      </>
                    ) : (
                      <label className="question">
                        <span className="sr-only">Research question</span>
                        <textarea
                          rows={4}
                          placeholder={
                            mode === "workflow"
                              ? "What should the research team investigate?"
                              : "What would you like to find in your sources?"
                          }
                          maxLength={2000}
                          {...register("question")}
                        />
                      </label>
                    )}
                    {mode === "workflow" && (
                      <details className="advanced">
                        <summary>
                          <SlidersHorizontal size={15} />
                          Workflow design & budgets
                        </summary>
                        <div className="stack">
                          <label>
                            Strategy
                            <select
                              value={strategy}
                              onChange={(e) => setStrategy(e.target.value)}
                            >
                              {[
                                ["auto", "Automatic plan"],
                                ["single_react", "Single research agent"],
                                ["collaborative", "Collaborative review"],
                                ["custom", "Custom task graph"],
                              ].map(([v, t]) => (
                                <option key={v} value={v}>
                                  {t}
                                </option>
                              ))}
                            </select>
                          </label>
                          {strategy === "custom" && (
                            <div>
                              Task graph JSON
                              <PlanEditor value={custom} change={setCustom} />
                            </div>
                          )}
                          <label>
                            Maximum model calls
                            <input
                              type="number"
                              min={1}
                              max={30}
                              required
                              value={budget}
                              onChange={(e) =>
                                setBudget(Number(e.target.value))
                              }
                            />
                          </label>
                          <label className="inline">
                            <input
                              type="checkbox"
                              checked={allowSearch}
                              onChange={(e) => setAllowSearch(e.target.checked)}
                            />
                            Allow public research search
                          </label>
                        </div>
                      </details>
                    )}
                    <div className="actions">
                      <small>
                        {mode === "language"
                          ? passage.length + " characters"
                          : selected.length +
                            " source" +
                            (selected.length === 1 ? "" : "s") +
                            " selected"}
                      </small>
                      <button className="primary" disabled={busy}>
                        {mode === "language" ? (
                          <ScanText size={16} />
                        ) : mode === "workflow" ? (
                          <GitBranch size={16} />
                        ) : (
                          <Search size={16} />
                        )}
                        {busy
                          ? "Working…"
                          : mode === "workflow"
                            ? "Launch workflow"
                            : mode === "search"
                              ? "Find passages"
                              : mode === "language"
                                ? "Analyze"
                                : "Get answer"}
                      </button>
                    </div>
                  </form>
                </Section>
                {mode === "workflow" && runId && (
                  <Section
                    title="Live workflow"
                    aside={
                      <span className="chip">
                        {run.data?.state ?? "Loading"}
                      </span>
                    }
                  >
                    <ErrorLine error={run.error} />
                    {activeRun && (
                      <>
                        <div className="readings">
                          <span>{activeRun.tool_calls} tool calls</span>
                          <span>{activeRun.llm_calls} LLM calls</span>
                          <span>{activeRun.tokens} tokens</span>
                        </div>
                        <Workflow run={activeRun} select={setNode} />
                        {node && (
                          <p>
                            <strong>{node.id}</strong> · {node.description}
                          </p>
                        )}
                        {activeRun.error && (
                          <p className="error">{activeRun.error}</p>
                        )}
                        <div className="button-row">
                          {!terminal.has(activeRun.state) && (
                            <button
                              disabled={busy}
                              onClick={() =>
                                action(async () => {
                                  await send(
                                    "/workflows/" +
                                      runId +
                                      "/cancel?project_id=" +
                                      project,
                                    {},
                                  );
                                  await run.refetch();
                                })
                              }
                            >
                              <Square size={14} />
                              Cancel run
                            </button>
                          )}
                          {["PENDING", "WAITING"].includes(activeRun.state) && (
                            <button
                              onClick={() =>
                                action(async () => {
                                  await send(
                                    "/workflows/" +
                                      runId +
                                      "/execute?project_id=" +
                                      project,
                                    {},
                                  );
                                  await run.refetch();
                                })
                              }
                            >
                              Resume
                            </button>
                          )}
                        </div>
                        {activeRun.report && (
                          <>
                            <h3>Research report</h3>
                            <p className="chip">
                              Verification ·{" "}
                              {activeRun.report.verification.outcome}
                            </p>
                            {activeRun.report.results.map((r, i) => (
                              <article key={i}>
                                <p>{r.summary}</p>
                                {r.evidence.map((e, j) => (
                                  <blockquote key={j}>
                                    {e.quote}
                                    <small>
                                      {e.document_id} / {e.chunk_id}
                                    </small>
                                  </blockquote>
                                ))}
                              </article>
                            ))}
                            <button
                              onClick={() =>
                                download(
                                  "research-report.md",
                                  markdown(activeRun),
                                )
                              }
                            >
                              <Download size={15} />
                              Download report
                            </button>
                          </>
                        )}
                      </>
                    )}
                  </Section>
                )}
                {result && <Results result={result} />}
              </div>
              <div>
                <Section
                  title="Source selection"
                  aside={
                    <button
                      aria-label="Open source library"
                      onClick={() => choose("library")}
                    >
                      <Plus size={16} />
                    </button>
                  }
                >
                  {sourcePicker()}
                  {mode === "language" && (
                    <button
                      disabled={!selected.length}
                      onClick={() => {
                        const d = docs.data?.find((d) => d.id === selected[0]);
                        if (d)
                          setValue(
                            "passage",
                            d.pages
                              .map((p) => p.text)
                              .join("\n")
                              .slice(
                                0,
                                languageOp === "similarity" ? 2000 : 20000,
                              ),
                          );
                      }}
                    >
                      Use first selected document
                    </button>
                  )}
                </Section>
                {mode === "language" && (
                  <Section title="Model evaluation">
                    <ModelBenchmarks />
                  </Section>
                )}
                {view === "answer" && (
                  <Section title="Latest workflow">
                    {recent ? (
                      <button
                        className="recent"
                        onClick={() => activate(recent.id)}
                      >
                        <GitBranch size={17} />
                        <span>
                          {recent.id.slice(0, 8)}
                          <small>
                            {new Date(recent.updated * 1000).toLocaleString()}
                          </small>
                        </span>
                        <span className="chip">{recent.state}</span>
                      </button>
                    ) : (
                      <p className="hint">
                        No saved workflows in this project.
                      </p>
                    )}
                  </Section>
                )}
              </div>
            </div>
          )}
          {mode === "library" && (
            <>
              {ingestion && (
                <p className="notice" role="status">
                  Ingestion {ingestion.id.slice(0, 8)} · {ingestion.status}
                  {ingestion.retryable && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(async () => {
                          const job = await send<Job>(
                            "/ingestion/jobs/" + ingestion.id + "/retry",
                            {},
                          );
                          await followJob(job);
                          setNotice("Source indexed.");
                        })
                      }
                    >
                      Retry ingestion
                    </button>
                  )}
                </p>
              )}
              <Section title="Import a source">
                <form
                  className="import"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void ingest();
                  }}
                >
                  <LinkIcon size={18} />
                  <input
                    aria-label="Source URL or arXiv ID"
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    placeholder="Paste a public URL or arXiv identifier"
                    required
                  />
                  <button disabled={busy}>Import</button>
                </form>
                <label className="chunk">
                  Chunking strategy
                  <select
                    value={chunk}
                    onChange={(e) => setChunk(e.target.value)}
                  >
                    {[
                      "recursive",
                      "fixed",
                      "sentence",
                      "structure",
                      "semantic",
                    ].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <small>
                  Uploads · PDF, DOCX, HTML, TXT, Markdown, CSV, PNG or JPEG · 5
                  MB per file
                </small>
              </Section>
              <Section
                title="Indexed documents"
                aside={
                  <span className="chip">
                    {docs.data?.length ?? "—"} sources
                  </span>
                }
              >
                <input
                  aria-label="Filter sources"
                  placeholder="Filter by filename"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
                {sourcePicker(true)}
              </Section>
            </>
          )}
          {mode === "history" && (
            <Section title="Saved workflows">
              <ErrorLine error={history.error} />
              {!history.data?.length && (
                <p className="hint">
                  {history.isLoading
                    ? "Loading…"
                    : "No workflows in this project."}
                </p>
              )}
              {history.data?.map((r) => (
                <button
                  className="history"
                  key={r.id}
                  onClick={() => activate(r.id)}
                >
                  <ClipboardList size={17} />
                  <span>{r.id.slice(0, 8)}</span>
                  <small>{new Date(r.updated * 1000).toLocaleString()}</small>
                  <span className="chip">{r.state}</span>
                </button>
              ))}
            </Section>
          )}
          {mode === "settings" && (
            <Settings
              key={project}
              project={project}
              switchProject={switchProject}
            />
          )}
          {trace && mode !== "history" && mode !== "settings" && (
            <Section
              title="Activity log"
              aside={
                <span className="chip">
                  <Activity size={13} /> {trace.id.slice(0, 8)}
                </span>
              }
            >
              <StageProgress rows={trace.events} />
              <Journal
                rows={
                  trace.events.length
                    ? trace.events
                    : mode === "workflow"
                      ? (journal.data?.events ?? [])
                      : []
                }
              />
              {trace.warning && <small>{trace.warning}</small>}
            </Section>
          )}
          {((mode === "workflow" && activeRun?.report) || result) &&
            !["settings", "history", "library"].includes(mode) && (
              <Section title="Source feedback">
                <div className="feedback">
                  <label>
                    Source
                    <select
                      value={feedbackSource}
                      onChange={(e) => setFeedbackSource(e.target.value)}
                    >
                      <option value="">Select source</option>
                      {docs.data?.map((d) => (
                        <option value={d.id} key={d.id}>
                          {d.filename}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Section
                    <input
                      maxLength={100}
                      value={feedbackSection}
                      onChange={(e) => setFeedbackSection(e.target.value)}
                    />
                  </label>
                  {([1, -1] as const).map((v) => (
                    <button
                      disabled={
                        busy || !feedbackSource || !feedbackSection.trim()
                      }
                      aria-label={
                        v === 1 ? "Helpful source" : "Unhelpful source"
                      }
                      key={v}
                      onClick={() =>
                        action(async () => {
                          await send(
                            "/projects/" + project + "/feedback",
                            {
                              document_id: feedbackSource,
                              section: feedbackSection,
                              vote: v,
                            },
                            undefined,
                            "PUT",
                          );
                          setNotice("Feedback saved.");
                        })
                      }
                    >
                      {v === 1 ? (
                        <ThumbsUp size={17} />
                      ) : (
                        <ThumbsDown size={17} />
                      )}
                    </button>
                  ))}
                </div>
              </Section>
            )}
        </div>
      </main>
    </div>
  );
}
export default function Workspace() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: false, refetchOnWindowFocus: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <Console />
    </QueryClientProvider>
  );
}
