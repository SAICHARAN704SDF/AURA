// Next's standalone bundle expects static assets and public files beside server.js.
// Docker copies these at image build time. Local npm start prepares the same layout.
import { cp } from "node:fs/promises";
await Promise.all([
  cp("public", ".next/standalone/public", { recursive: true }),
  cp(".next/static", ".next/standalone/.next/static", { recursive: true }),
]);
process.env.HOSTNAME = process.env.RESEARCHOS_WEB_HOST || "127.0.0.1";
process.env.PORT ||= "3000";
await import("../.next/standalone/server.js");
