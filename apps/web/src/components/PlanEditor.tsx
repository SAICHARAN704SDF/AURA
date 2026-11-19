"use client";
import Editor, { loader } from "@monaco-editor/react";
loader.config({ paths: { vs: "/monaco/vs" } });
export default function PlanEditor({
  value,
  change,
}: {
  value: string;
  change: (v: string) => void;
}) {
  return (
    <Editor
      height="300px"
      language="json"
      value={value}
      onChange={(v) => change(v ?? "")}
      loading="Loading JSON editor…"
      options={{
        ariaLabel: "Task graph JSON",
        minimap: { enabled: false },
        automaticLayout: true,
        fontSize: 13,
        scrollBeyondLastLine: false,
      }}
    />
  );
}
