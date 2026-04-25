#!/usr/bin/env bash
# SayAi — install from a local clone (Linux/macOS).
# Windows: python -m pip install -e ".[dev]" && python -m sayai db init
# VPS hints: ./install.sh --vps
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--vps" ]]; then
  echo "[SayAi] Example systemd unit (copy and edit User/WorkingDirectory/paths):"
  echo "        $ROOT/docs/vps-sayai.service.example"
  if [[ -f "$ROOT/docs/vps-sayai.service.example" ]]; then
    echo "---"
    cat "$ROOT/docs/vps-sayai.service.example"
  fi
  echo ""
  echo "After install: uv run sayai server   # health on http://127.0.0.1:8765/health"
  echo "Put overrides in ~/.config/sayai/settings.yaml and API keys in ~/.config/sayai/.env"
  exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[SayAi] Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
fi

uv sync
uv run sayai db init

echo "[SayAi] Done. Start TUI: uv run sayai tui"
echo "         Config: ~/.config/sayai/settings.yaml and ~/.config/sayai/.env"
