# SayAi — AI-OS (Phase 1–5)

Self-hosted foundation: **PostgreSQL**, **Redis**, **Qdrant**, **FastAPI** with **JWT + API keys**, **health checks**, and **CI**.

Phase 2 adds **LiteLLM-backed runs** (chat + agent tool loops), **WebSocket streaming**, **built-in skills**, **session memory** (Postgres + Redis cache), and **run traces** (`run_steps`).

Phase 3 adds **RAG** (ingest → chunk → embed → Qdrant upsert → semantic query + optional grounded answer) and **workflows** (store React Flow JSON, execute a DAG of `wfInput` / `wfLlm` / `wfRag` / `wfOutput` nodes, with **WebSocket** streaming + traces).

Phase 4 adds a **product shell**: per-user **skill settings** (`user_skill_settings`), **observability** (`GET /api/v1/observability/summary`), **run listings** (`GET /api/v1/runs`, `GET /api/v1/workflow-runs`), **Compose profiles** (`full` = Qdrant + Next.js UI; default/low = Postgres + Redis + API only), and **`install.sh`** for a one-command self-hosted boot.

Phase 5 (**Growth**) adds **skill discovery drafts** (`skill_discovery_drafts` + `GET/POST/PATCH/DELETE /api/v1/skill-drafts`), **marketplace-style packs** on disk (`packages/backend/skill_packs/*/manifest.json` + `GET /api/v1/skill-packs`, optional `SKILL_PACKS_EXTRA_DIRS`), **stronger tool sandboxing** (SSRF-safe URL checks for `sayai.http_get`, optional `SKILL_HTTP_HOST_ALLOWLIST`, bounded execution time via `SKILL_TOOL_TIMEOUT_SECONDS` + thread pool), and a **Kubernetes baseline** under `deploy/k8s/` (multi-replica Deployment, Service, HPA, PDB).

## Tutorial VPS (Bahasa Indonesia, dari nol)

Lihat **[TUTORIAL-VPS.md](TUTORIAL-VPS.md)** — push ke `https://github.com/anutmagang/SayAi.git`, bootstrap satu skrip, `.env`, firewall, dan uji API.

## Prerequisites

- Docker Engine + Docker Compose v2

## Quick start

**Linux / macOS (recommended for a VPS)**

**Satu skrip VPS (Docker + clone opsional + Compose):** `bootstrap-vps.sh` memasang Docker (via [get.docker.com](https://get.docker.com)) jika belum ada, lalu menjalankan `install.sh`.

```bash
# Sudah git clone ke folder SayAi:
cd /path/to/SayAi && sudo ./bootstrap-vps.sh
SAYAI_PROFILE=full sudo ./bootstrap-vps.sh

# VPS “kosong” — set URL repo Anda, lalu:
export SAYAI_REPO_URL='https://github.com/USER/SayAi.git'
curl -fsSL https://raw.githubusercontent.com/USER/SayAi/main/bootstrap-vps.sh | sudo -E bash -s
```

**Hanya stack SayAi (Docker sudah terpasang):**

```bash
cd /path/to/SayAi
chmod +x install.sh
./install.sh              # API + Postgres + Redis
SAYAI_PROFILE=full ./install.sh   # also Qdrant + Next.js
```

**Windows (PowerShell)**

```powershell
cd c:\Users\ASUS\Videos\SayAi
Copy-Item .env.example .env
docker compose up --build -d
docker compose --profile full up --build -d   # optional: Qdrant + frontend
```

Optional: edit `.env` to set `POSTGRES_PASSWORD` and `SECRET_KEY` before the first boot. For API-only Compose (no Qdrant), set `QDRANT_URL=` empty so `/api/v1/health/ready` does not wait on Qdrant.

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Liveness: `GET http://localhost:8000/health`
- Readiness (DB + Redis + Qdrant): `GET http://localhost:8000/api/v1/health/ready`

### First user

1. `POST /api/v1/auth/register` with `email` + `password` (min 8 chars) → first user becomes **owner**.
2. `POST /api/v1/auth/login` → JWT `access_token`.
3. `GET /api/v1/auth/me` with `Authorization: Bearer <jwt>`.

### API keys

- Create: `POST /api/v1/auth/api-keys` (JWT), returns `secret` **once** (`sayai_…`).
- Use: `Authorization: Bearer <secret>` or `X-API-Key: <secret>`.

### Runs (Phase 2)

Set `OPENAI_API_KEY` in `.env` (or your LiteLLM-supported provider env vars).

- `GET /api/v1/skills` — list built-in skills + JSON Schemas
- `GET /api/v1/skills/settings` — merged catalog + per-user enabled/config
- `PATCH /api/v1/skills/settings/{skill_id}` / `DELETE …` — toggle or clear overrides
- `GET /api/v1/runs` — recent runs (limit)
- `GET /api/v1/observability/summary?window_hours=…` — run counts + token sums + workflow run count
- `POST /api/v1/runs` — start a **chat** or **agent** run (creates a `session_id` if omitted)
- `GET /api/v1/runs/{run_id}` — status + token usage + summary
- `GET /api/v1/runs/{run_id}/trace` — ordered execution steps (LLM + tool)
- `WS /api/v1/runs/{run_id}/stream?access_token=<jwt_or_api_key>` — JSON event stream (Redis-backed)

`POST /api/v1/runs` supports `await_completion: true` for synchronous completion (useful for scripts/tests).

### RAG + workflows (Phase 3)

RAG:

- `POST /api/v1/rag/collections`
- `GET /api/v1/rag/collections`
- `DELETE /api/v1/rag/collections/{id}` (also drops the Qdrant collection)
- `POST /api/v1/rag/collections/{id}/documents` (JSON `{title,text}`)
- `GET /api/v1/rag/collections/{id}/documents`
- `POST /api/v1/rag/collections/{id}/query` (`{query, top_k, answer}`)

Workflows:

- `POST /api/v1/workflows` / `GET /api/v1/workflows` / `GET/PUT /api/v1/workflows/{id}`
- `POST /api/v1/workflows/{id}/runs` (`{inputs, await_completion}`)
- `GET /api/v1/workflow-runs` / `GET /api/v1/workflow-runs/{id}` / `GET /api/v1/workflow-runs/{id}/trace`
- `WS /api/v1/workflow-runs/{id}/stream?access_token=...`

### Web UI (Phase 3–4)

A **Next.js + Tailwind + React Flow** UI lives in `packages/frontend`. The `frontend` service uses the **`full`** Compose profile (see above).

Then open:

- UI: `http://localhost:3000` (with `--profile full`)
- Skill manager: `/skills`
- Debug / observability: `/debug`
- Skill discovery drafts: `/drafts`
- API docs: `http://localhost:8000/docs`

### Growth APIs (Phase 5)

- `GET/POST /api/v1/skill-drafts`, `GET/PATCH/DELETE /api/v1/skill-drafts/{id}` — discovery pipeline JSON (`body` is free-form; typical keys: `proposed_id`, `extends_skill_id`, `notes`).
- `GET /api/v1/skill-packs` — catalog of discovered `manifest.json` files on the API host.

See `packages/backend/skill_packs/README.md` and `deploy/k8s/README.md`.

## Layout

```text
SayAi/
├── docker-compose.yml
├── install.sh
├── bootstrap-vps.sh
├── deploy/k8s/           # HA / scale starting point (Kustomize)
├── .env.example
├── README.md
├── .github/workflows/ci.yml
├── packages/backend/     # FastAPI app + Alembic + skill_packs/
└── packages/frontend/    # Next.js + React Flow UI
```

## Local backend (without Docker)

```powershell
cd packages/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:SECRET_KEY="local-dev-secret-key-at-least-32-chars"
$env:DATABASE_URL="postgresql+psycopg://sayai:sayai@127.0.0.1:5432/sayai"
$env:REDIS_URL="redis://127.0.0.1:6379/0"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Phase roadmap (5 phases)

1. **Foundation (this repo state)** — compose stack, auth, health, CI  
2. Core runtime — LiteLLM, runs, agents, skills  
3. RAG + workflows — ingest, React Flow execution  
4. Product shell — installer polish, Compose profiles, skills + debug UI, observability  
5. Growth — discovery drafts, pack manifests, sandboxed tools, K8s baseline

## License

Add your license (e.g. MIT) when you publish.
