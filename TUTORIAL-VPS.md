# Tutorial lengkap SayAi di VPS (dari nol)

Panduan ini memakai repositori: **https://github.com/anutmagang/SayAi.git**

Anggap VPS **Ubuntu 22.04/24.04 LTS** (atau Debian 12), akses **SSH** sebagai user dengan `sudo`, dan alamat publik misalnya `203.0.113.10`.

---

## Bagian A — Kode sudah di GitHub (Anda / kami push ke `anutmagang/SayAi`)

Jika repo sudah berisi kode, di VPS Anda cukup **clone** (lewati Bagian B di laptop).

---

## Bagian B — Push dari laptop ke GitHub (sekali saja)

Lakukan di folder project SayAi di komputer Anda.

### B.1 Buat repositori di GitHub

1. Buka https://github.com/new  
2. Nama repositori: **SayAi**  
3. **Jangan** centang “Add a README” (biar kosong, nanti diisi dari push lokal).  
4. Buat repositori.

### B.2 Login Git ke GitHub

Pilih salah satu:

- **HTTPS:** saat `git push`, Git meminta **Personal Access Token** (bukan password akun). Buat token: GitHub → Settings → Developer settings → Personal access tokens. Scope minimal: `repo`.  
- **SSH:** tambahkan kunci SSH di GitHub (Settings → SSH keys), lalu remote pakai `git@github.com:anutmagang/SayAi.git`.

### B.3 Perintah push (contoh HTTPS)

```bash
cd /path/ke/folder/SayAi
git init
git add -A
git commit -m "Initial commit: SayAi"
git branch -M main
git remote add origin https://github.com/anutmagang/SayAi.git
git push -u origin main
```

Jika `git remote` sudah ada dan salah:

```bash
git remote remove origin
git remote add origin https://github.com/anutmagang/SayAi.git
git push -u origin main
```

Jika push ditolak karena repo tidak kosong, ikuti pesan error GitHub atau gunakan `git pull origin main --allow-unrelated-histories` lalu push lagi (hati-hati konflik).

---

## Bagian C — Persiapan VPS

### C.1 Login SSH

```bash
ssh root@203.0.113.10
# atau user biasa:
ssh ubuntu@203.0.113.10
```

### C.2 Update sistem

```bash
sudo apt update && sudo apt upgrade -y
```

### C.3 (Opsional) Buat user non-root dengan sudo

Jika masih pakai root saja, bisa dilewati. Untuk produksi, user khusus lebih baik.

---

## Bagian D — Instal SayAi otomatis (satu skrip)

Di VPS, **pilih salah satu** cara berikut.

### D.1 Paling praktis: `bootstrap-vps.sh` (Docker + clone + Compose)

Skrip memasang **Docker** (lewat skrip resmi get.docker.com) jika belum ada, meng-clone repo ke **`/opt/sayai`**, lalu menjalankan **`install.sh`**.

```bash
export SAYAI_REPO_URL='https://github.com/anutmagang/SayAi.git'
curl -fsSL https://raw.githubusercontent.com/anutmagang/SayAi/main/bootstrap-vps.sh | sudo -E bash -s
```

**Stack lengkap** (Qdrant + UI Next.js):

```bash
export SAYAI_REPO_URL='https://github.com/anutmagang/SayAi.git'
export SAYAI_PROFILE=full
curl -fsSL https://raw.githubusercontent.com/anutmagang/SayAi/main/bootstrap-vps.sh | sudo -E bash -s
```

> Catatan: baris `curl` di atas baru berhasil setelah branch **main** di GitHub berisi file `bootstrap-vps.sh` (setelah push pertama selesai).

### D.2 Manual: clone lalu `install.sh`

Jika Docker sudah terpasang:

```bash
sudo apt update
sudo apt install -y git
cd /opt
sudo git clone https://github.com/anutmagang/SayAi.git
cd SayAi
sudo chmod +x install.sh bootstrap-vps.sh
sudo ./install.sh
# atau penuh:
sudo SAYAI_PROFILE=full ./install.sh
```

---

## Bagian E — Konfigurasi `.env` (wajib dibaca)

File ada di folder instalasi, misalnya **`/opt/sayai/.env`** (atau path clone Anda).

```bash
sudo nano /opt/sayai/.env
```

Ubah minimal:

| Variabel | Isi |
|----------|-----|
| `POSTGRES_PASSWORD` | Password kuat |
| `SECRET_KEY` | Hasil `openssl rand -hex 32` di VPS |
| `OPENAI_API_KEY` | Kunci API OpenAI (atau sesuai provider LiteLLM) |

**Mode API saja** (tanpa Qdrant di compose “low”): kosongkan agar health tidak menunggu Qdrant:

```env
QDRANT_URL=
```

Simpan (`Ctrl+O`, Enter, `Ctrl+X` di nano).

Jika stack sudah jalan, setelah edit `.env` jalankan ulang:

```bash
cd /opt/sayai
sudo docker compose down && sudo docker compose up -d
# atau profile full:
sudo docker compose --profile full down && sudo docker compose --profile full up -d
```

---

## Bagian F — Firewall (UFW)

Buka SSH dan port yang dipakai:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8000/tcp comment 'SayAi API'
# Jika pakai profile full + UI:
sudo ufw allow 3000/tcp comment 'SayAi UI'
sudo ufw enable
sudo ufw status
```

**Produksi:** lebih aman pakai **Nginx/Caddy** di port **443**, proxy ke `127.0.0.1:8000`, dan **tidak** membuka 8000 ke internet langsung.

---

## Bagian G — Uji SayAi

Ganti `IP_VPS` dengan IP publik Anda.

- **API:** http://IP_VPS:8000  
- **Swagger:** http://IP_VPS:8000/docs  
- **Health:** http://IP_VPS:8000/health  
- **UI** (jika `full`): http://IP_VPS:3000  

### User pertama (owner)

1. Buka **Swagger** → `POST /api/v1/auth/register`  
2. Body JSON: `{"email":"admin@domainanda.com","password":"minimal8huruf"}`  
3. Login dengan `POST /api/v1/auth/login` → simpan `access_token`.

Di UI (`/login`), pastikan **`NEXT_PUBLIC_API_URL`** di `.env` / build mengarah ke URL API yang bisa dijangkau **dari browser** (bukan `http://localhost:8000` jika akses dari luar VPS — gunakan `http://IP_VPS:8000` atau domain HTTPS).

---

## Bagian H — Perintah Docker berguna

```bash
cd /opt/sayai
sudo docker compose ps
sudo docker compose logs -f api
sudo docker compose restart api
```

---

## Ringkasan satu halaman

1. Buat repo **SayAi** di GitHub (user **anutmagang**).  
2. Push kode dari laptop (`git init` → `commit` → `remote` → `push main`).  
3. Di VPS: `export SAYAI_REPO_URL='https://github.com/anutmagang/SayAi.git'` → `curl … bootstrap-vps.sh | sudo -E bash -s`.  
4. Edit **`/opt/sayai/.env`**: password DB, `SECRET_KEY`, `OPENAI_API_KEY`, `QDRANT_URL=` untuk mode low.  
5. Buka port **8000** (dan **3000** jika full), uji **/docs**, register user pertama.

---

## Pemulihan: `git: command not found` lalu `./install.sh: No such file or directory`

Versi bootstrap lama menjalankan **clone sebelum** `git` terpasang. **Perbaikan sudah di `main` di GitHub** — jalankan ulang bootstrap **setelah** tarik skrip terbaru, atau lakukan manual:

```bash
sudo apt-get update && sudo apt-get install -y git
# Hapus folder gagal (jika ada dan kosong / tidak lengkap):
sudo rm -rf /opt/sayai
export SAYAI_REPO_URL='https://github.com/anutmagang/SayAi.git'
curl -fsSL https://raw.githubusercontent.com/anutmagang/SayAi/main/bootstrap-vps.sh | sudo -E bash -s
```

**Atau** tanpa curl ulang (Docker Anda sudah OK):

```bash
sudo apt-get install -y git
sudo rm -rf /opt/sayai
sudo git clone --depth 1 https://github.com/anutmagang/SayAi.git /opt/sayai
cd /opt/sayai && sudo chmod +x install.sh && sudo ./install.sh
```

---

## Masalah umum

| Gejala | Tindakan |
|--------|----------|
| `curl bootstrap-vps.sh` 404 | Pastikan branch **main** sudah ter-push dan nama file benar. |
| `git: command not found` saat bootstrap | Pakai skrip **terbaru** dari `main`, atau `apt-get install -y git` lalu ulang (lihat bagian Pemulihan di atas). |
| Docker permission denied | Jalankan compose dengan `sudo`, atau `sudo usermod -aG docker $USER` lalu logout/login. |
| `/health/ready` merah tanpa Qdrant | Set `QDRANT_URL=` kosong di `.env`. |
| UI tidak hit API | Set `NEXT_PUBLIC_API_URL` ke URL publik API, rebuild frontend / pakai profile full dengan env benar. |

Jika butuh bantuan spesifik (log error, screenshot), kirim pesan error persis dari terminal atau Swagger.
