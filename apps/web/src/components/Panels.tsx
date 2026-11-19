import { useState, type ReactNode } from "react";
import { download, type EventRow } from "../lib/api";
export const names = (key: string) => key.replaceAll("_", " ");
export function Section({
  title,
  children,
  aside,
}: {
  title: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="section-title">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
export function ErrorLine({ error }: { error: unknown }) {
  return error instanceof Error ? (
    <div className="error" role="alert">
      {error.message}
    </div>
  ) : null;
}
export function Journal({ rows }: { rows: EventRow[] }) {
  const [filter, setFilter] = useState("");
  const matches = rows.filter((row) =>
    JSON.stringify(row).toLowerCase().includes(filter.toLowerCase()),
  );
  if (!rows.length) return <p className="hint">Waiting for recorded events.</p>;
  return (
    <>
      <div className="log-tools">
        <input
          type="search"
          aria-label="Filter events"
          placeholder="Filter by step, status or tool"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <button
          onClick={() =>
            download(
              "workflow-events.json",
              JSON.stringify(rows, null, 2),
              "application/json",
            )
          }
        >
          Export events
        </button>
      </div>
      <ol className="journal">
        {matches
          .slice()
          .reverse()
          .map((r) => (
            <li key={r.sequence}>
              <details>
                <summary>
                  <time>{new Date(r.time * 1000).toLocaleTimeString()}</time>
                  <b>{names(r.stage ?? r.type ?? "Event")}</b>
                  <span>{r.tool ?? r.task_id ?? ""}</span>
                  <small>
                    {r.status ?? r.state}
                    {r.http_status ? " · " + r.http_status : ""}
                  </small>
                </summary>
                <dl>
                  {Object.entries(r)
                    .filter(
                      ([k]) =>
                        !["time", "stage", "type", "status", "state"].includes(
                          k,
                        ),
                    )
                    .map(([k, v]) => (
                      <div key={k}>
                        <dt>{names(k)}</dt>
                        <dd>
                          {typeof v === "object"
                            ? JSON.stringify(v)
                            : String(v)}
                        </dd>
                      </div>
                    ))}
                </dl>
              </details>
            </li>
          ))}
      </ol>
      {!matches.length && <p>No matching events.</p>}
    </>
  );
}
