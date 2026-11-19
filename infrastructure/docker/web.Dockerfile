FROM node:22-bookworm-slim AS build
WORKDIR /web
ENV NEXT_TELEMETRY_DISABLED=1 AURA_API_ORIGIN=http://api:8000
COPY apps/web/package*.json ./
COPY apps/web/scripts/editor-assets.mjs scripts/editor-assets.mjs
RUN npm ci --no-audit --no-fund
COPY apps/web/next.config.mjs apps/web/tsconfig.json apps/web/postcss.config.mjs ./
COPY apps/web/src/ ./src/
RUN npm run build

FROM node:22-bookworm-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
WORKDIR /web
COPY --from=build --chown=node:node /web/.next/standalone/ ./
COPY --from=build --chown=node:node /web/.next/static/ ./.next/static/
COPY --from=build --chown=node:node /web/public/ ./public/
USER node
EXPOSE 3000
CMD ["node", "server.js"]
