#!/bin/bash
set -eu
: "${RESEARCHOS_PASSWORD_HASH:?Set a bcrypt hash for the researcher login}"
python -m uvicorn aura.api:app --host 127.0.0.1 --port 8000 --workers 1 &
api=$!
PORT=3000 HOSTNAME=127.0.0.1 node /web/server.js &
web=$!
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
gateway=$!
cleanup() {
    kill "$api" "$web" "$gateway" 2>/dev/null || true
    wait || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
wait -n
exit 1
