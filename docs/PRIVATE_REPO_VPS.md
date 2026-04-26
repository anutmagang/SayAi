# SayAi di VPS — repo **privat** atau pelanggan tanpa akses GitHub Anda

Panduan singkat (Bahasa Indonesia) untuk developer / penjual self-hosted.

---

## 1. Apa bedanya publik vs privat?

- **Publik:** `git clone https://github.com/org/SayAi.git` langsung jalan.
- **Privat:** GitHub menolak clone tanpa **bukti identitas** (token atau kunci SSH).

Instalasi SayAi setelah kode ada di disk **sama** — pakai `install-vps-lengkap.sh install` dari folder repo.

---

## 2. Opsi A — HTTPS + Personal Access Token (PAT)

1. Di GitHub: **Settings → Developer settings → Personal access tokens** — buat token (scope minimal: **repo** untuk repo privat).
2. Di VPS (jangan rekam token di skrip yang di-commit):

   ```bash
   git clone "https://ISI_TOKEN_DISINI@github.com/ORG/SayAi.git" SayAi
   cd SayAi
   chmod +x install-vps-lengkap.sh
   ./install-vps-lengkap.sh install --with-system-deps
   ```

3. Setelah clone berhasil, **credential helper** (opsional) atau deploy key bisa dipakai agar `git pull` tidak mengetik token setiap kali.

**Keamanan:** jangan kirim token lewat chat tidak terenkripsi; rotasi token jika bocor.

---

## 3. Opsi B — SSH key di VPS (disarankan untuk server)

1. Di VPS:

   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "sayai-vps"
   cat ~/.ssh/id_ed25519.pub
   ```

2. Salin baris `ssh-ed25519 ...` ke GitHub:
   - **Deploy key** (hanya satu repo), atau
   - **SSH keys** di akun GitHub (semua repo yang diizinkan).

3. Clone:

   ```bash
   git clone git@github.com:ORG/SayAi.git SayAi
   cd SayAi
   ./install-vps-lengkap.sh install --with-system-deps
   ```

---

## 4. Opsi C — ZIP / artefak (pelanggan tidak pakai git)

1. Anda (developer) buat rilis: **Download ZIP** dari GitHub atau `git archive`.
2. Kirim file ke pelanggan (aman sesuai kebijakan Anda).
3. Di VPS:

   ```bash
   unzip SayAi-main.zip -d SayAi
   cd SayAi-main   # atau nama folder hasil unzip
   ./install-vps-lengkap.sh install --with-system-deps
   ```

Pastikan folder berisi **`pyproject.toml`** dan **`sayai/`**.

---

## 5. Setelah install (semua opsi)

- Edit `~/.config/sayai/.env` (API key) dan `~/.config/sayai/settings.yaml` (model).
- Lihat juga **`./install-vps-lengkap.sh tutorial`** di dalam repo.
- **Skill** isi database: aktifkan SkillHunter di konfigurasi → `sayai hunt` → `sayai admin` untuk menyetujui — lihat `docs/TUTORIAL.md`.

---

## 6. Mengganti remote lokal dari SayAi-Dev ke SayAi

Jika Anda sudah punya clone lama:

```bash
git remote set-url origin https://github.com/anutmagang/SayAi.git
# atau
git remote set-url origin git@github.com:anutmagang/SayAi.git
git fetch origin
git branch -u origin/main main   # sesuaikan nama branch
```

---

*Dokumen ini melengkapi `install-vps-lengkap.sh` dan `docs/TUTORIAL.md`.*
