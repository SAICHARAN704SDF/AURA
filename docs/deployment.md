# Run ResearchOS on one machine

Docker Compose runs the Next.js research workspace and a single FastAPI process. The web server forwards same-origin API requests to the API container. AURA's SQLite files, document metadata, locally stored Qdrant vectors, workflow checkpoints and ingestion queue live together under the API's data mount. The container includes the English spaCy pipeline, English OCR data and the OpenCode CLI used by the AgentRouter adapter.

## Start

Use Docker Engine or Docker Desktop with Compose 2.24 or later. Run the following from the repository root. The first build downloads Python and Node packages, the spaCy model and container images.

```sh
mkdir -p data
export RESEARCHOS_CONTAINER_USER="$(id -u):$(id -g)"
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open the research workspace at [localhost:3000](http://localhost:3000). API documentation is available at [localhost:8000/docs](http://localhost:8000/docs). Both host ports bind to loopback. This deployment is intended for a single trusted user.

The API reads the root `.env` at container startup. Point `RESEARCHOS_ENV_FILE` at a separate file for isolated tests. The frontend receives no provider keys. Configure the same model and embedding services used by your native AURA installation. A successful health request checks the process. Upload, retrieval and generation exercise the configured providers. For Ollama running on macOS outside Docker, use the Docker Desktop hostname `host.docker.internal` in the compatible endpoint configuration.

## Use existing research or a separate demo library

The default bind mount is `./data`. Stop any native AURA process using this directory before starting Compose with that mount. Embedded Qdrant requires exclusive access. Set `RESEARCHOS_DATA_DIR` to a different directory to run both applications at the same time. Set the two port variables when native services already occupy the defaults.

```sh
export RESEARCHOS_DATA_DIR="$(mktemp -d)"
export RESEARCHOS_API_PORT=18080 RESEARCHOS_WEB_PORT=13000
export RESEARCHOS_CONTAINER_USER="$(id -u):$(id -g)"
docker compose -p researchos-demo up --build -d
```

Open [localhost:13000](http://localhost:13000) for this example. Upload a short paper through **Source library**, wait for its indexing job to finish, then search for a passage. The job API accepts uploads and public URLs, persists queued input and recovers interrupted jobs when the API restarts.

## Operations

```sh
docker compose logs -f api web
docker compose restart api
docker compose down
```

Use the same `-p researchos-demo` option for a separately named instance. `down` removes its containers and network. The host data directory persists. Stop the service before copying the entire data directory for a consistent backup of SQLite and Qdrant. Restore a backup into a separate directory and point `RESEARCHOS_DATA_DIR` there. If the host reports a database write-permission error, verify the configured container UID and the directory's ownership.

CI installs the locked frontend dependencies, runs lint, checks TypeScript, builds the application and executes the offline Chromium workflow tests. For independent browser testing from the checkout, install the root Python test dependencies and English spaCy model, then run `npm ci`, `npx playwright install chromium` and `npm test` from `apps/web`.
