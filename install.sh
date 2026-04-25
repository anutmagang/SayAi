#!/usr/bin/env bash
# SayAi self-hosted installer — Docker Compose with optional "full" profile (Qdrant + UI).
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash   # when published
#   ./install.sh                  # SAYAI_PROFILE=low (default): postgres, redis, API only
#   SAYAI_PROFILE=full ./install.sh   # also Qdrant + Next.js frontend
#
# Environment:
#   SAYAI_PROFILE   low | full (default: low)
#   Extra CLI args are forwarded to `docker compose … up` (e.g. ./install.sh --force-recreate)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine + Compose v2, then re-run." >&2
  exit 1
fi

if [[ ! -f docker-compose.yml ]]; then
  echo "Run this script from the SayAi repository root (docker-compose.yml missing)." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "Created .env from .env.example — set POSTGRES_PASSWORD, SECRET_KEY, and OPENAI_API_KEY."
  else
    echo "Missing .env.example; create a .env file manually before continuing." >&2
    exit 1
  fi
fi

PROFILE="${SAYAI_PROFILE:-low}"

if [[ "$PROFILE" == "full" ]]; then
  echo "Starting SayAi (profile=full: API + Postgres + Redis + Qdrant + frontend)…"
  docker compose --profile full up --build -d "$@"
else
  echo "Starting SayAi (profile=low: API + Postgres + Redis). RAG/Qdrant UI are omitted."
  echo "Tip: set QDRANT_URL= (empty) in .env so /api/v1/health/ready skips Qdrant when it is not running."
  docker compose up --build -d "$@"
fi

echo "API: http://localhost:8000  (set API_PORT in .env to change host mapping)"
if [[ "$PROFILE" == "full" ]]; then
  echo "UI:  http://localhost:3000  (set FRONTEND_PORT in .env to change host mapping)"
fi
