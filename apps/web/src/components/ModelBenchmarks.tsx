"use client";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "../lib/api";

type Scores = {
  ner_exact_span: { precision: number; recall: number; f1: number };
  relation_exact_triple: { f1: number };
  extractive_summary: { rougeL: number };
};
type Checkpoint = {
  name: string;
  base: string;
  train_documents: number;
  test_documents: number;
  off_the_shelf: Scores;
  fine_tuned: Scores;
};
export default function ModelBenchmarks() {
  const models = useQuery({
    queryKey: ["ner-models"],
    queryFn: () =>
      api<{ active: string; checkpoints: Checkpoint[] }>("/nlp/models"),
  });
  return (
    <>
      <small>Active pipeline · {models.data?.active ?? "Loading…"}</small>
      {models.error && <p role="alert">{models.error.message}</p>}
      {models.data && !models.data.checkpoints.length && (
        <p className="hint">
          No trained checkpoints registered in this deployment.
        </p>
      )}
      {models.data?.checkpoints.map((c) => (
        <article key={c.name}>
          <h3>{c.name}</h3>
          <p className="hint">
            {c.base} · {c.train_documents} training and {c.test_documents}{" "}
            held-out documents
          </p>
          <div style={{ width: "100%", height: 160 }}>
            <ResponsiveContainer>
              <BarChart
                data={[
                  {
                    label: "Baseline",
                    value: c.off_the_shelf.ner_exact_span.f1,
                  },
                  {
                    label: "Fine-tuned",
                    value: c.fine_tuned.ner_exact_span.f1,
                  },
                ]}
              >
                <XAxis dataKey="label" />
                <YAxis domain={[0, 1]} width={35} />
                <Tooltip />
                <Bar
                  name="Exact-span F1"
                  dataKey="value"
                  fill="#42473f"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table>
            <caption>Held-out scores</caption>
            <thead>
              <tr>
                <th>Measure</th>
                <th>Base</th>
                <th>Tuned</th>
              </tr>
            </thead>
            <tbody>
              {(["precision", "recall", "f1"] as const).map((m) => (
                <tr key={m}>
                  <td>NER {m}</td>
                  <td>{c.off_the_shelf.ner_exact_span[m].toFixed(3)}</td>
                  <td>{c.fine_tuned.ner_exact_span[m].toFixed(3)}</td>
                </tr>
              ))}
              <tr>
                <td>Relation F1</td>
                <td>{c.off_the_shelf.relation_exact_triple.f1.toFixed(3)}</td>
                <td>{c.fine_tuned.relation_exact_triple.f1.toFixed(3)}</td>
              </tr>
              <tr>
                <td>ROUGE-L</td>
                <td>{c.off_the_shelf.extractive_summary.rougeL.toFixed(3)}</td>
                <td>{c.fine_tuned.extractive_summary.rougeL.toFixed(3)}</td>
              </tr>
            </tbody>
          </table>
        </article>
      ))}
    </>
  );
}
