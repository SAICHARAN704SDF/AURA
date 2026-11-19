// Serve the editor's worker and language assets from the researcher's own host.
import { cp, mkdir } from "node:fs/promises";
await mkdir("public/monaco", { recursive: true });
await cp("node_modules/monaco-editor/min/vs", "public/monaco/vs", {
  recursive: true,
});
