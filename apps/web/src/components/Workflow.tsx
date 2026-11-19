"use client";
import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Position,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Run, Task } from "../lib/api";

export default function Workflow({
  run,
  select,
}: {
  run: Run;
  select: (task: Task) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const tasks = run.plan?.tasks ?? [];
    const levels = new Map<string, number>();
    const depth = (id: string): number => {
      if (levels.has(id)) return levels.get(id)!;
      const deps = tasks.find((t) => t.id === id)?.dependencies ?? [];
      const value = deps.length ? 1 + Math.max(...deps.map(depth)) : 0;
      levels.set(id, value);
      return value;
    };
    const widths = new Map<number, number>();
    const nodes = tasks.map((task) => {
      const y = depth(task.id);
      const x = widths.get(y) ?? 0;
      widths.set(y, x + 1);
      const state = run.tasks[task.id]?.state ?? "PENDING";
      return {
        id: task.id,
        position: { x: x * 224, y: y * 115 },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
        data: {
          label: (
            <>
              <strong>{task.id}</strong>
              <small>
                {task.agent} · {state.toLowerCase()}
              </small>
            </>
          ),
        },
        className: "task-node " + state.toLowerCase(),
      };
    });
    return {
      nodes,
      edges: tasks.flatMap((task) =>
        task.dependencies.map((id) => ({
          id: id + "-" + task.id,
          source: id,
          target: task.id,
          markerEnd: { type: MarkerType.ArrowClosed },
        })),
      ),
    };
  }, [run]);
  if (!nodes.length)
    return (
      <p className="hint">
        The planner’s task graph will appear here when its plan is saved.
      </p>
    );
  return (
    <div className="graph">
      <ReactFlow
        key={run.id + ":" + nodes.length}
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        minZoom={0.25}
        maxZoom={1.4}
        onNodeClick={(_, n) => {
          const t = run.plan?.tasks.find((t) => t.id === n.id);
          if (t) select(t);
        }}
      >
        <Background gap={18} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
