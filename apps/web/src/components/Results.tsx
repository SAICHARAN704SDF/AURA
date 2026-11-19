import { Download } from "lucide-react";
import { download, type Result } from "../lib/api";
import KnowledgeGraph from "./KnowledgeGraph";
import { Section, names } from "./Panels";

export default function Results({ result }: { result: Result }) {
  return (
    <Section
      title={result.title}
      aside={
        <button
          aria-label="Download result as JSON"
          onClick={() =>
            download(
              "research-result.json",
              JSON.stringify(result.raw, null, 2),
              "application/json",
            )
          }
        >
          <Download size={16} />
        </button>
      }
    >
      {result.text && <p className="prose">{result.text}</p>}
      {result.review && (
        <details className="advanced">
          <summary>
            Claim review · {result.review.outcome} · {result.usage} reported
            tokens
          </summary>
          {result.review.claims?.map((r, i) => (
            <p key={i}>
              {r.claim} <span className="chip">{r.outcome}</span>
            </p>
          ))}
        </details>
      )}
      {result.analysis && (
        <>
          <div className="readings">
            <span>{result.analysis.tokens.length} tokens</span>
            <span>{result.analysis.sentences.length} sentences</span>
            <span>Language · {result.analysis.language.code}</span>
          </div>
          <h3>Entities</h3>
          <div className="tags">
            {result.analysis.entities.map((e) => (
              <span className="chip" key={e.start}>
                {e.text} · {e.label}
              </span>
            ))}
            {!result.analysis.entities.length && "No entities found."}
          </div>
          <h3>Relationships</h3>
          {result.analysis.relations.length > 0 && (
            <KnowledgeGraph relations={result.analysis.relations} />
          )}
          {result.analysis.relations.map((r, i) => (
            <blockquote key={i}>
              {r.subject.text} → {names(r.predicate)} → {r.object.text}
              <small>{r.evidence}</small>
            </blockquote>
          ))}
          {!result.analysis.relations.length && (
            <p>No relationships matched.</p>
          )}
          <h3>Coreference</h3>
          {result.analysis.coreference.length ? (
            result.analysis.coreference.map((c, i) => (
              <p key={i}>
                {c.mention} → {c.antecedent.text}
              </p>
            ))
          ) : (
            <p>No unambiguous references found.</p>
          )}
        </>
      )}
      {result.passages?.map((p, i) => (
        <blockquote key={i}>
          {p.text}
          <small>
            {p.filename}
            {p.page ? " · page " + p.page : ""} {p.id}
          </small>
        </blockquote>
      ))}
      {result.passages?.length === 0 && <p>No passages returned.</p>}
    </Section>
  );
}
