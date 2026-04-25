# SayAi

Platform coding berbasis agen: orkestrator (Planner → DAG → agregator), memori (SQLite, opsional Qdrant/Redis), SkillHunter, dan TUI.

## Mulai cepat

- **Windows:** `python -m pip install -e ".[dev]"` lalu `python -m sayai db init`
- **Linux/macOS:** `./install.sh` (membutuhkan [uv](https://github.com/astral-sh/uv))
- **VPS (satu skrip = tutorial + instal otomatis):** file **`install-vps-lengkap.sh`** di root repo. Setelah `install`, pengguna cukup mengedit **`~/.config/sayai/.env`** (API key) dan **`~/.config/sayai/settings.yaml`** (satu baris model `x-model-saya`). Perintah: `./install-vps-lengkap.sh tutorial` lalu `./install-vps-lengkap.sh install --with-system-deps`

Konfigurasi: `%USERPROFILE%\.config\sayai\settings.yaml` dan `.env` di folder yang sama (atau `SAYAI_CONFIG_DIR`).

## Dokumentasi lengkap

Lihat **[docs/TUTORIAL.md](docs/TUTORIAL.md)** — instalasi, variabel lingkungan, perintah CLI, SkillHunter, admin, memori, server health, dan pemecahan masalah.

Blueprint arsitektur: [SayAi_Project_Blueprint.md](SayAi_Project_Blueprint.md).

## Perintah singkat

| Perintah | Fungsi |
|----------|--------|
| `sayai tui` | TUI interaktif |
| `sayai run "..."` | Satu tugas ke stdout |
| `sayai db init` | Inisialisasi SQLite |
| `sayai index` | Indeks folder ke Qdrant (jika diaktifkan) |
| `sayai hunt` | SkillHunter |
| `sayai admin` | TUI admin proposal skill |
| `sayai server` | HTTP `/health` |
| `sayai session export` | Stub ekspor sesi (JSON) |
| `sayai plugins` | Daftar `*.py` di direktori plugin |

## Lisensi

MIT (lihat repositori).
