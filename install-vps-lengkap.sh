#!/usr/bin/env bash
# =============================================================================
# SayAi — instalasi VPS + tutorial (satu file)
# =============================================================================
#   ./install-vps-lengkap.sh tutorial   → cetak panduan langkah demi langkah
#   ./install-vps-lengkap.sh install    → instal dependensi proyek (dari root klon)
#   ./install-vps-lengkap.sh install --with-system-deps
#                                       → + apt (Ubuntu/Debian) untuk paket sistem
#
# Repositori resmi contoh: https://github.com/anutmagang/SayAi-Dev.git
# =============================================================================
set -euo pipefail

REPO_URL_DEFAULT="https://github.com/anutmagang/SayAi-Dev.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_tutorial() {
  cat <<'TUTOR'

================================================================================
  SayAi — TUTORIAL VPS (langkah demi langkah)
================================================================================

Ringkasan: Anda butuh VPS Linux (disarankan Ubuntu 24.04 LTS agar Python 3.12
ada secara default), kunci API LLM, dan opsional Qdrant/Redis.

--------------------------------------------------------------------------------
A. Apa yang WAJIB diubah / disiapkan
--------------------------------------------------------------------------------

1) Lokasi kode di VPS
   - Disarankan: /opt/sayai atau $HOME/SayAi-Dev
   - Setelah clone, jalankan skrip instal dari ROOT folder repo (ada pyproject.toml).

2) File ~/.config/sayai/.env  (kunci API — RAHASIA, jangan di-commit)
   Salin dari .env.example di repo, lalu isi minimal salah satu provider yang
   modelnya Anda pakai di settings.yaml:

     ANTHROPIC_API_KEY=sk-ant-...     → https://console.anthropic.com/
     OPENAI_API_KEY=sk-...           → https://platform.openai.com/api-keys
     GEMINI_API_KEY=...              → https://aistudio.google.com/apikey
     GROQ_API_KEY=gsk_...            → https://console.groq.com/keys
     OPENROUTER_API_KEY=sk-or-...    → https://openrouter.ai/keys

   Cara mendapatkannya: buka URL di atas → daftar/login → buat API key → tempel
   di .env satu baris per variabel. Model di LiteLLM memakai id seperti
   anthropic/claude-3-5-haiku-20241022 — pastikan provider yang dipakai sudah
   punya kunci di .env.

3) File ~/.config/sayai/settings.yaml  (opsional tapi disarankan)
   Override YAML di-merge dengan sayai/config/defaults.yaml. Ubah misalnya:
     llm.default_model, llm.routing, memory.qdrant_enabled, memory.redis_url,
     orchestrator.use_dag, server.host, server.port, features.*

4) Systemd (service jalan otomatis)
   Edit docs/vps-sayai.service.example:
     User=...           → user Linux Anda (whoami)
     WorkingDirectory=  → path folder repo
     ExecStart=         → path ke .../bin/sayai server --host 0.0.0.0 --port 8765
   Salin ke /etc/systemd/system/sayai.service lalu:
     sudo systemctl daemon-reload && sudo systemctl enable --now sayai

5) Firewall / security group (cloud provider)
   - Buka port SSH (22) dari IP Anda saja jika bisa.
   - Port 8765 (health) atau reverse proxy: hanya dari load balancer / IP yang perlu.
   - Jangan expose .env ke web.

--------------------------------------------------------------------------------
B. Urutan kerja di VPS (manual singkat)
--------------------------------------------------------------------------------

  sudo apt update && sudo apt install -y git curl
  git clone REPO_URL_DEFAULT
  cd SayAi-Dev    # atau nama folder hasil clone
  chmod +x install-vps-lengkap.sh install.sh
  ./install-vps-lengkap.sh install --with-system-deps   # Ubuntu/Debian + uv + sync + db
  mkdir -p ~/.config/sayai
  cp .env.example ~/.config/sayai/.env
  nano ~/.config/sayai/.env        # isi API key
  uv run sayai server --host 0.0.0.0 --port 8765   # uji health

  Cek: curl -s http://127.0.0.1:8765/health

--------------------------------------------------------------------------------
C. Dokumentasi tambahan
--------------------------------------------------------------------------------

  docs/TUTORIAL.md              — panduan umum CLI & fitur
  docs/vps-sayai.service.example — template systemd
  README.md

--------------------------------------------------------------------------------
D. Catatan Python
--------------------------------------------------------------------------------

  Proyek membutuhkan Python >= 3.11. Ubuntu 24.04: paket python3.12 tersedia.
  Ubuntu 22.04: pasang python3.11 (mis. deadsnakes PPA) atau upgrade OS.

================================================================================
TUTOR
  echo ""
  echo "Repo contoh clone:"
  echo "  git clone ${REPO_URL_DEFAULT}"
  echo ""
}

is_repo_root() {
  [[ -f "${SCRIPT_DIR}/pyproject.toml" ]] && [[ -d "${SCRIPT_DIR}/sayai" ]]
}

install_system_deps_apt() {
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[SayAi] sudo tidak ada; lewati paket sistem atau jalankan sebagai root."
    return 0
  fi
  echo "[SayAi] Memasang paket sistem (apt)..."
  sudo apt-get update -y
  sudo apt-get install -y git curl ca-certificates build-essential
  if apt-cache show python3.12 &>/dev/null; then
    sudo apt-get install -y python3.12 python3.12-venv python3-pip
  else
    sudo apt-get install -y python3 python3-venv python3-pip
  fi
}

install_uv_if_needed() {
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if ! command -v uv >/dev/null 2>&1; then
    echo "[SayAi] Memasang uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  fi
}

copy_config_templates() {
  local cfg="${HOME}/.config/sayai"
  mkdir -p "${cfg}"
  if [[ ! -f "${cfg}/.env" ]] && [[ -f "${SCRIPT_DIR}/.env.example" ]]; then
    cp "${SCRIPT_DIR}/.env.example" "${cfg}/.env"
    echo "[SayAi] Dibuat ${cfg}/.env — edit dan isi API key (nano/vim)."
  elif [[ -f "${cfg}/.env" ]]; then
    echo "[SayAi] ${cfg}/.env sudah ada, tidak ditimpa."
  fi
}

run_install() {
  local with_sys="${1:-}"

  if ! is_repo_root; then
    echo "[SayAi] ERROR: jalankan dari root repositori (berisi pyproject.toml dan folder sayai/)."
    echo "        git clone ${REPO_URL_DEFAULT} && cd SayAi-Dev && ./install-vps-lengkap.sh install"
    exit 1
  fi

  cd "${SCRIPT_DIR}"

  if [[ "${with_sys}" == "--with-system-deps" ]]; then
    if [[ -f /etc/debian_version ]]; then
      install_system_deps_apt
    else
      echo "[SayAi] Bukan Debian/Ubuntu: lewati apt. Pasang Python 3.11+ dan git secara manual."
    fi
  fi

  install_uv_if_needed
  # Pastikan interpreter >= 3.11 (uv bisa mengunduh Python jika perlu).
  uv python install 3.12 2>/dev/null || uv python install 3.11 2>/dev/null || true
  uv sync
  uv run sayai db init
  copy_config_templates

  echo ""
  echo "[SayAi] Selesai."
  echo "  • Konfig:  ~/.config/sayai/settings.yaml  dan  ~/.config/sayai/.env"
  echo "  • TUI:     uv run sayai tui"
  echo "  • Health:  uv run sayai server --host 0.0.0.0 --port 8765"
  echo "  • Tutorial penuh: ./install-vps-lengkap.sh tutorial"
}

case "${1:-}" in
  tutorial|help|-h|--help)
    print_tutorial
    ;;
  install)
    shift || true
    run_install "${1:-}"
    ;;
  *)
    echo "Pemakaian:"
    echo "  $0 tutorial                    # panduan VPS + API key + systemd"
    echo "  $0 install                     # uv sync + db init (dari root repo)"
    echo "  $0 install --with-system-deps  # + apt di Ubuntu/Debian"
    exit 1
    ;;
esac
