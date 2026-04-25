# Tutorial SayAi

Panduan praktis untuk menginstal, mengonfigurasi, dan menjalankan SayAi dari nol. Bahasa utama: **Indonesia**; istilah teknis tetap dalam bentuk yang umum dipakai di CLI dan konfigurasi.

---

## 1. Apa itu SayAi?

SayAi adalah lingkungan **agen AI untuk coding**: satu atau banyak agen (misalnya penulis kode, reviewer, pencari konteks) diorkestrasi lewat **Planner → DAG (gelombang paralel) → Aggregator**, dengan opsi mode **sederhana** (satu `CoderAgent` saja).

Fitur tambahan:

- **Memori:** SQLite (skill store, proposal), opsional **Qdrant** (RAG) dan **Redis** (scratchpad sesi).
- **SkillHunter:** merayapi sumber publik, menganalisis, menulis ulang ke **proposal skill**; persetujuan lewat **admin TUI**.
- **Server health:** HTTP minimal `GET /health` untuk VPS atau probe.
- **Opsional:** refleksi setelah DAG (`features.reflect_after_dag`), log penggunaan token ke file (`features.cost_log_path`).

Detail arsitektur ada di `SayAi_Project_Blueprint.md` di root proyek.

---

## 2. Persyaratan

- **Python 3.11+**
- Kunci API untuk model yang dipakai LiteLLM (misalnya Anthropic, OpenAI, Google, Groq — sesuai string model di `settings.yaml`).
- Opsional: **Qdrant**, **Redis**, **uv** (disarankan di Linux/macOS).

---

## 3. Instalasi

### 3.1 Windows (PowerShell)

Dari folder klon repositori:

```powershell
cd C:\path\to\SayAi
python -m pip install -e ".[dev]"
python -m sayai db init
```

Jalankan TUI:

```powershell
python -m sayai tui
```

### 3.2 Linux / macOS dengan `install.sh`

Skrip memakai **uv** bila tersedia; jika belum, akan mengarahkan instalasi uv.

```bash
chmod +x install.sh
./install.sh
```

Setelah selesai, contoh menjalankan TUI:

```bash
uv run sayai tui
```

### 3.3 VPS — satu skrip (tutorial + instal otomatis)

**Lokasi skrip:** `install-vps-lengkap.sh` (folder root proyek, sejajar `pyproject.toml`).

**Lokasi template model minimal:** `docs/settings.pengguna-minimal.yaml` — otomatis disalin ke `~/.config/sayai/settings.yaml` saat pertama kali menjalankan `install` (jika file belum ada).

Di server Linux, dari **root folder** hasil `git clone`:

```bash
chmod +x install-vps-lengkap.sh
./install-vps-lengkap.sh tutorial    # panduan lengkap: API key, systemd, firewall
./install-vps-lengkap.sh install --with-system-deps
```

Setelah itu, untuk pemakaian dasar cukup:

1. Edit **`~/.config/sayai/.env`** — isi API key provider yang dipakai model Anda.
2. Edit **`~/.config/sayai/settings.yaml`** — ubah **satu baris** `x-model-saya: &m "..."` (id model LiteLLM).

Repositori contoh: `https://github.com/anutmagang/SayAi-Dev.git`

### 3.4 Mode VPS (petunjuk systemd ringkas)

Tanpa skrip di atas, cetak contoh unit systemd:

```bash
./install.sh --vps
```

File contoh: `docs/vps-sayai.service.example`. Sesuaikan `User`, `WorkingDirectory`, path venv, dan `ExecStart` (misalnya `sayai server --host 0.0.0.0 --port 8765`).

---

## 4. Konfigurasi

### 4.1 Lokasi file

Secara default SayAi membaca:


| Lokasi                                                                                     | Isi                                      |
| ------------------------------------------------------------------------------------------ | ---------------------------------------- |
| `%USERPROFILE%\.config\sayai\settings.yaml` (Windows) atau `~/.config/sayai/settings.yaml` | Override YAML                            |
| File `.env` di folder yang sama                                                            | Variabel lingkungan (API key, URL, dll.) |


Anda bisa mengarahkan folder konfigurasi dengan variabel lingkungan `**SAYAI_CONFIG_DIR**`.

Nilai default bawaan paket ada di `sayai/config/defaults.yaml`; pengaturan pengguna **menggabungkan** (deep merge) ke default tersebut.

### 4.2 Variabel lingkungan (prefix `SAYAI_`)

Pydantic Settings mendukung nested delimiter `__`. Contoh (nama field mengikuti `AppSettings` di `sayai/config/settings.py`):

- `SAYAI_LLM__DEFAULT_MODEL=anthropic/claude-3-5-haiku-20241022`
- `SAYAI_MEMORY__QDRANT_ENABLED=true`
- `SAYAI_MEMORY__REDIS_URL=redis://localhost:6379/0`

Letakkan kunci API provider di `.env`, misalnya:

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

(LiteLLM membaca env standar provider; lihat dokumentasi LiteLLM untuk model yang dipilih.)

### 4.3 Cuplikan `settings.yaml`

```yaml
llm:
  default_model: anthropic/claude-3-5-haiku-20241022
  routing:
    planning: anthropic/claude-3-5-haiku-20241022
    coding: anthropic/claude-3-5-haiku-20241022

memory:
  qdrant_enabled: false
  qdrant_url: http://localhost:6333
  redis_url: ""

orchestrator:
  use_dag: true

server:
  host: 127.0.0.1
  port: 8765

features:
  reflect_after_dag: false
  cost_log_path: ""   # contoh: /var/log/sayai/usage.jsonl

skillhunter:
  enabled: false
  github_query: "mcp server in:name,description,readme"
```

- `**orchestrator.use_dag`:** `true` = Planner + DAG + agregator; `false` atau flag CLI `--simple` = satu agen penulis kode.
- `**features.reflect_after_dag`:** setelah output DAG digabung, satu panggilan LLM tambahan untuk bullet risiko/follow-up.
- `**features.cost_log_path`:** jalan file; setiap completion non-stream yang punya `usage` dari LiteLLm menambahkan satu baris JSON (model + token).

---

## 5. Perintah CLI

Semua perintah di bawah ini setelah instalasi: `sayai ...` atau `python -m sayai ...`.

### 5.1 `sayai tui`

TUI interaktif (Textual).

```text
sayai tui [--cwd PATH] [--simple]
```

- `**--cwd`:** direktori kerja untuk tool (default: cwd saat ini).
- `**--simple`:** paksa mode tanpa planner/DAG (satu agen).

### 5.2 `sayai run`

Menjalankan satu **task** string, stream ke stdout.

```text
sayai run "Tulis fungsi hello" [--cwd PATH] [--simple]
```

Berguna untuk skrip CI atau uji cepat orkestrator.

### 5.3 `sayai db init`

Membuat/memperbarui skema SQLite di direktori data (`data_dir`, default `~/.local/share/sayai`).

### 5.4 `sayai index`

Mengindeks teks dari folder ke Qdrant (harus `memory.qdrant_enabled: true` dan Qdrant jalan).

```text
sayai index [--cwd .] [--max-files 400]
```

### 5.5 `sayai hunt`

Menjalankan **SkillHunter** (crawler + analyzer + rewriter) dan menulis proposal ke store (SQLite).

Pastikan `skillhunter` dan kredensial jaringan/API sesuai kebutuhan sumber (GitHub token, dll.) jika diperlukan oleh implementasi crawler Anda.

### 5.6 `sayai admin`

TUI admin: melihat proposal, versi, menyetujui/menolak, dll. (lihat `sayai/cli/admin.py`).

### 5.7 `sayai server`

Server HTTP sangat ringan:

- `**GET /`**, `**GET /health`**, `**GET /healthz**` → JSON `{"ok":true,"service":"sayai"}`.

```text
sayai server [--host HOST] [--port PORT]
```

Default host/port dari `settings.yaml` → blok `server`.

### 5.8 `sayai session export`

Menulis file JSON kecil (placeholder) untuk alur “berbagi sesi” di masa depan.

```text
sayai session export [--out PATH]
```

Tanpa `--out`, file dibuat di `data_dir/sessions/<uuid>.json`.

### 5.9 `sayai plugins`

Mencetak daftar file `*.py` di `data_dir/plugins/`. Folder dibuat otomatis jika belum ada. Ini **hook ekstensi** sederhana untuk workflow Anda sendiri (pemuatan dinamis lanjutan dapat ditambahkan di rilis berikutnya).

---

## 6. Alur SkillHunter + Admin (ringkas)

1. Setel query dan batasan di `skillhunter` pada `settings.yaml`.
2. Jalankan `sayai db init` jika belum.
3. `sayai hunt` → proposal masuk sebagai **pending**.
4. `sayai admin` → review, diff, approve/reject; versi skill disimpan sesuai skema DB (`skill_versions`, `store_revision`).

---

## 7. Memori (Qdrant & Redis)

- **Qdrant:** aktifkan `memory.qdrant_enabled`, set URL dan koleksi, pastikan layanan Qdrant berjalan, lalu `sayai index` untuk bulk index; agen dapat memakai RAG sesuai implementasi tool/memori proyek.
- **Redis:** isi `memory.redis_url`; scratchpad sesi disinkronkan di akhir alur orkestrator DAG (dan mode tertentu) agar konteks antar gelombang tersimpan.

---

## 8. Pengujian pengembang

```bash
pytest -q
```

atau dengan uv:

```bash
uv run pytest -q
```

---

## 9. Pemecahan masalah


| Gejala                    | Yang dicek                                                                                                                               |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Model gagal / timeout     | Rantai fallback di `llm.fallback_chains`; kunci API di `.env`; koneksi jaringan.                                                         |
| Qdrant error              | `qdrant_enabled`, URL, dimensi embedding vs koleksi.                                                                                     |
| Redis tidak terhubung     | `redis_url`, firewall, TLS jika dipakai.                                                                                                 |
| SQLite / kolom hilang     | Jalankan `sayai db init` lagi setelah upgrade; pastikan `data_dir` sama dengan yang dipakai tes (monkeypatch `db_path` hanya untuk tes). |
| Port server sudah dipakai | Ganti `server.port` atau `sayai server --port ...`.                                                                                      |


---

## 10. Ringkasan file penting


| Path                                        | Peran                          |
| ------------------------------------------- | ------------------------------ |
| `sayai/main.py`                             | Entry CLI Click                |
| `sayai/config/settings.py`, `defaults.yaml` | Model konfigurasi              |
| `sayai/orchestrator/`                       | Planner, DAG, pool, aggregator |
| `sayai/agents/`                             | Agen (coder, reviewer, dll.)   |
| `sayai/memory/`                             | Qdrant, indexer, scratchpad    |
| `sayai/skillhunter/`                        | Pipeline hunt                  |
| `sayai/db/`                                 | SQLite + skill store           |
| `docs/TUTORIAL.md`                          | Dokumen ini                    |
| `docs/vps-sayai.service.example`            | Contoh systemd                 |


---

*Terakhir diselaraskan dengan fitur CLI dan konfigurasi di repositori SayAi. Jika perilaku CLI berubah, utamakan `sayai --help` dan sumber kode di `sayai/main.py`.*