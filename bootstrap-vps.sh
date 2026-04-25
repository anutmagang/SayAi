#!/usr/bin/env bash
# SayAi — bootstrap satu skrip untuk VPS (Debian/Ubuntu): Docker + clone (opsional) + install.sh
#
# Cara A — sudah punya folder hasil git clone:
#   cd SayAi && sudo ./bootstrap-vps.sh
#   SAYAI_PROFILE=full sudo ./bootstrap-vps.sh
#
# Cara B — VPS kosong, hanya curl skrip ini (WAJIB set URL repo Anda):
#   export SAYAI_REPO_URL='https://github.com/PEMILIK/SayAi.git'
#   curl -fsSL https://raw.githubusercontent.com/PEMILIK/SayAi/main/bootstrap-vps.sh | sudo -E bash -s
#
# Opsional:
#   SAYAI_HOME=/opt/sayai   (default: /opt/sayai)
#   SAYAI_PROFILE=full      (default: low — tanpa Qdrant/UI di compose)
#
# Skrip ini memanggil https://get.docker.com — tinjau di server produksi sebelum pakai.

set -euo pipefail

SAYAI_HOME="${SAYAI_HOME:-/opt/sayai}"
SAYAI_PROFILE="${SAYAI_PROFILE:-low}"

usage() {
  cat <<'EOF'
SayAi bootstrap (VPS)

  Sudah clone repo:
    cd /path/to/SayAi && sudo ./bootstrap-vps.sh

  VPS kosong + URL Git:
    export SAYAI_REPO_URL='https://github.com/USER/SayAi.git'
    curl -fsSL .../bootstrap-vps.sh | sudo -E bash -s

Opsional: SAYAI_HOME, SAYAI_PROFILE=full
EOF
}

for arg in "$@"; do
  if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
    usage
    exit 0
  fi
done

if [[ "${1:-}" == "--repo" && -n "${2:-}" ]]; then
  SAYAI_REPO_URL="$2"
  shift 2
fi

need_root() {
  if [[ "${EUID:-0}" -ne 0 ]]; then
    echo "Jalankan dengan root, contoh: sudo bash $0" >&2
    exit 1
  fi
}

need_root

# Git harus ada sebelum clone; dulu git baru dipasang di install_docker() setelah clone → gagal di VPS minimal.
ensure_git_when_cloning() {
  if [[ -z "${SAYAI_REPO_URL:-}" ]]; then
    return 0
  fi
  if command -v git &>/dev/null; then
    return 0
  fi
  if ! command -v apt-get &>/dev/null; then
    echo "git tidak terpasang dan apt-get tidak ada. Pasang git manual, lalu ulangi." >&2
    exit 1
  fi
  echo "==> Memasang git (diperlukan untuk clone repo)…" >&2
  apt-get update -qq
  apt-get install -y git curl ca-certificates
}

have_compose() {
  if docker compose version &>/dev/null; then
    return 0
  fi
  return 1
}

have_docker() {
  command -v docker &>/dev/null && have_compose
}

install_docker() {
  echo "==> Memasang Docker Engine + Compose (get.docker.com)…"
  apt-get update -qq
  apt-get install -y ca-certificates curl git
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
  systemctl enable --now docker 2>/dev/null || true
}

detect_repo_from_script() {
  local src
  src="${BASH_SOURCE[0]:-}"
  if [[ -z "$src" || "$src" == "-" ]]; then
    return 1
  fi
  if [[ ! -f "$src" ]]; then
    return 1
  fi
  local dir
  dir="$(cd "$(dirname "$src")" && pwd)"
  if [[ -f "$dir/docker-compose.yml" ]]; then
    echo "$dir"
    return 0
  fi
  return 1
}

resolve_repo_root() {
  local detected=""
  if detected="$(detect_repo_from_script)"; then
    echo "$detected"
    return 0
  fi
  if [[ -n "${SAYAI_REPO_URL:-}" ]]; then
    if [[ -f "$SAYAI_HOME/docker-compose.yml" ]]; then
      echo "$(cd "$SAYAI_HOME" && pwd)"
      return 0
    fi
    if [[ -e "$SAYAI_HOME" ]]; then
      echo "SAYAI_HOME=$SAYAI_HOME sudah ada tetapi bukan checkout SayAi (tidak ada docker-compose.yml)." >&2
      echo "Hapus folder itu atau ubah SAYAI_HOME, lalu ulangi." >&2
      exit 1
    fi
    echo "==> Meng-clone SayAi ke $SAYAI_HOME …" >&2
    mkdir -p "$(dirname "$SAYAI_HOME")"
    if ! git clone --depth 1 "$SAYAI_REPO_URL" "$SAYAI_HOME"; then
      echo "git clone gagal. Periksa URL, jaringan, atau pasang: apt-get install -y git" >&2
      exit 1
    fi
    if [[ ! -f "$SAYAI_HOME/docker-compose.yml" ]]; then
      echo "Clone selesai tetapi docker-compose.yml tidak ada di $SAYAI_HOME" >&2
      exit 1
    fi
    echo "$(cd "$SAYAI_HOME" && pwd)"
    return 0
  fi
  echo "Tidak menemukan docker-compose.yml dari posisi skrip, dan SAYAI_REPO_URL kosong." >&2
  echo "Set: export SAYAI_REPO_URL='https://github.com/…/SayAi.git' lalu ulangi." >&2
  usage >&2
  exit 1
}

ensure_git_when_cloning

REPO_ROOT="$(resolve_repo_root)"
if [[ -z "$REPO_ROOT" || ! -f "$REPO_ROOT/docker-compose.yml" ]]; then
  echo "Gagal: folder SayAi tidak valid (REPO_ROOT kosong atau tanpa docker-compose.yml)." >&2
  exit 1
fi
echo "==> Folder SayAi: $REPO_ROOT"

if ! have_docker; then
  if ! command -v apt-get &>/dev/null; then
    echo "Skrip ini memasang Docker lewat apt (Debian/Ubuntu). apt-get tidak ditemukan." >&2
    echo "Pasang Docker Engine + plugin Compose manual, lalu jalankan ./install.sh di folder SayAi." >&2
    exit 1
  fi
  install_docker
fi

if ! have_docker; then
  echo "Docker/Compose masih tidak terdeteksi. Periksa instalasi manual." >&2
  exit 1
fi

echo "==> Docker OK: $(docker --version)"
docker compose version

if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
  echo "==> Menambahkan user '$SUDO_USER' ke grup docker (logout/login agar efek tanpa sudo)…"
  usermod -aG docker "$SUDO_USER" || true
fi

chmod +x "$REPO_ROOT/install.sh" "$REPO_ROOT/bootstrap-vps.sh" 2>/dev/null || true

echo "==> Menjalankan install.sh (SAYAI_PROFILE=$SAYAI_PROFILE)…"
export SAYAI_PROFILE
( cd "$REPO_ROOT" && ./install.sh "$@" )

echo ""
echo "Selesai. API biasanya di port 8000 (cek .env: API_PORT)."
echo "Dokumentasi API: http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000/docs  (ganti IP publik VPS)"
if [[ "$SAYAI_PROFILE" == "full" ]]; then
  echo "UI Next.js: port 3000 (profile full)."
fi
echo "Edit $REPO_ROOT/.env — set POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY."
if [[ "${SAYAI_PROFILE:-low}" != "full" ]]; then
  echo "Mode low: set QDRANT_URL= kosong di .env agar /health/ready tidak menunggu Qdrant."
fi
