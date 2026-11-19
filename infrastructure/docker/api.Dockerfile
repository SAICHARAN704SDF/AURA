FROM node:22-bookworm-slim AS opencode
RUN npm install --global opencode-ai@1.19.5

FROM python:3.12-slim-bookworm AS api
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/workspace/backend/src TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata DATA_DIR=/workspace/data
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr-eng libgomp1 \
    && find /var/lib/apt/lists -type f -delete
COPY --chmod=755 infrastructure/docker/api-entrypoint.sh /usr/local/bin/researchos-start
COPY pyproject.toml ./
# Install dependency wheels before source so edits do not invalidate model setup.
RUN --mount=type=cache,target=/root/.cache/pip python -c 'import tomllib; print("\n".join(tomllib.load(open("pyproject.toml","rb"))["project"]["dependencies"]))' > /tmp/requirements \
    && pip install -r /tmp/requirements \
    && python -m spacy download en_core_web_sm \
    && useradd --uid 10001 --user-group --no-create-home researchos \
    && mkdir -p /workspace/data \
    && chown researchos:researchos /workspace/data
COPY --from=opencode /usr/local/lib/node_modules/opencode-ai/bin/opencode.exe /opt/researchos-cli-bin
RUN install -m 755 /opt/researchos-cli-bin /usr/local/bin/opencode && /usr/local/bin/opencode --version
COPY backend/src/ ./backend/src/
COPY frontend/ ./frontend/
USER researchos
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/researchos-start"]
CMD ["python", "-m", "uvicorn", "aura.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM node:22-bookworm-slim AS webbuild
WORKDIR /web
ENV NEXT_TELEMETRY_DISABLED=1 AURA_API_ORIGIN=http://127.0.0.1:8000
COPY apps/web/package*.json ./
COPY apps/web/scripts/editor-assets.mjs scripts/editor-assets.mjs
RUN npm ci --no-audit --no-fund
COPY apps/web/next.config.mjs apps/web/tsconfig.json apps/web/postcss.config.mjs ./
COPY apps/web/src/ ./src/
RUN npm run build


FROM caddy:2-alpine AS gateway
FROM api AS render
COPY --from=webbuild /usr/local/bin/node /usr/local/bin/node
COPY --from=webbuild /web/.next/standalone/ /web/
COPY --from=webbuild /web/.next/static/ /web/.next/static/
COPY --from=webbuild /web/public/ /web/public/
COPY --from=gateway /usr/bin/caddy /usr/local/bin/caddy
COPY infrastructure/docker/Caddyfile /etc/caddy/Caddyfile
COPY --chmod=755 infrastructure/docker/render-start.sh /usr/local/bin/render-start
ENV PORT=10000 AURA_API_ORIGIN=http://127.0.0.1:8000
EXPOSE 10000
CMD ["/usr/local/bin/render-start"]
