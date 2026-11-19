"use client";
import { ReactFlow, Background, Controls, MarkerType } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
type Entity = { text: string; label: string };
type Relation = {
  subject: Entity;
  predicate: string;
  object: Entity;
  evidence: string;
};
export default function KnowledgeGraph({
  relations,
}: {
  relations: Relation[];
}) {
  const visible = relations.slice(0, 30);
  const id = (e: Entity) => e.label + ":" + e.text;
  const entries = [
    ...new Map(
      visible.flatMap((r) => [r.subject, r.object]).map((e) => [id(e), e]),
    ).values(),
  ];
  const nodes = entries.map((e, i) => ({
    id: id(e),
    position: { x: (i % 3) * 230, y: Math.floor(i / 3) * 115 + (i % 2) * 45 },
    data: {
      label: (
        <>
          <b>{e.text}</b>
          <small>{e.label}</small>
        </>
      ),
    },
    className: "task-node",
  }));
  const edges = visible.map((r, i) => ({
    id: String(i),
    source: id(r.subject),
    target: id(r.object),
    label: r.predicate.replaceAll("_", " "),
    markerEnd: { type: MarkerType.ArrowClosed },
  }));
  return (
    <div className="graph" aria-label="Knowledge graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background gap={18} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
