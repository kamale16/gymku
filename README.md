# GymKu

Aplikasi manajemen gym berbasis web: admin mengelola akun dan stok alat, trainer menyusun rencana latihan dan mencatat progres member, member melihat latihan dan perkembangannya sendiri.

**Demo:** _tempel link Render di sini setelah deploy_

## Tampilan
![Login](docs/1-login.png)
![Admin: akun](docs/2-admin-akun.png)
![Admin: alat](docs/3-admin-alat.png)
![Trainer](docs/4-trainer.png)
![Rencana latihan](docs/5-rencana.png)
![Member](docs/6-member.png)
![Member di HP](docs/7-member-hp.png)

## Fitur
- Tiga peran (admin, trainer, member) dengan pembatasan akses per peran
- Admin: tambah, hapus akun; keanggotaan member (masa aktif dan perpanjangan); stok alat
- Trainer: buat rencana latihan, terapkan ke member, catat progres harian (good / average / poor)
- Member: lihat rencana latihan, status keanggotaan, grafik dan riwayat progres
- Password di-hash, proteksi CSRF, query terparameter (aman dari SQL injection)
- 8 tes otomatis dengan pytest, dijalankan di SQLite dan PostgreSQL

## Tech stack
Python 3, Flask (blueprint + application factory), SQLite (lokal) / PostgreSQL (produksi), Jinja2, pytest, gunicorn.

## Menjalankan di komputer
```bash
git clone <url-repo-kamu>
cd gymku
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
flask --app app run --debug
```
Buka http://127.0.0.1:5000. Database dibuat otomatis di folder `instance/` dengan data demo.

| Peran | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Trainer | budi | budi1234 |
| Member | siti | siti1234 |

Reset database: `flask --app app init-db --demo` (tanpa `--demo` untuk database kosong, hanya akun admin).

## Tes
```bash
python -m pytest
```

## Deploy (Render, gratis)
1. Push ke GitHub, lalu di Render buat **Web Service** dari repo ini.
2. Build command: `pip install -r requirements.txt`. Start command: `gunicorn "app:create_app()"`.
3. Environment variables: `SECRET_KEY` (string acak panjang), `ADMIN_PASSWORD`, dan `SEED_DEMO=1` untuk demo.

Catatan: disk Render gratis bersifat sementara, jadi data SQLite akan kembali ke data demo saat layanan di-restart. Untuk data permanen, pindah ke PostgreSQL.

## Database: SQLite dan PostgreSQL
- **Lokal dan tes:** SQLite otomatis (file di `instance/`), tanpa instalasi.
- **Produksi:** isi environment variable `DATABASE_URL` (format `postgresql://...`) dan aplikasi memakai PostgreSQL. Tabel dan data demo dibuat otomatis saat database masih kosong.
- Menjalankan tes yang sama di PostgreSQL: `TEST_DATABASE_URL=postgresql://user:pass@host/db python -m pytest`

## Deploy ke Vercel + Neon (PostgreSQL)
Vercel mendeteksi Flask otomatis dan mencari variabel `app` di `index.py`; CSS dan logo dilayani dari folder `public/`.
1. Push repo ke GitHub, lalu di vercel.com pilih **Add New > Project** dan impor repo ini.
2. Buat database: di dashboard proyek Vercel buka **Storage / Marketplace**, pasang **Neon**, dan hubungkan ke proyek. Integrasi ini mengisi `DATABASE_URL` (versi pooled) otomatis. Alternatif manual: buat proyek di neon.com, salin connection string yang memakai `-pooler`, lalu tempel sebagai `DATABASE_URL`.
3. Tambahkan environment variables: `SECRET_KEY` (acak panjang), `ADMIN_PASSWORD`, `SEED_DEMO=1`.
4. Klik **Deploy** (atau **Redeploy** kalau database baru dihubungkan).

Tanpa `DATABASE_URL`, di Vercel aplikasi memakai SQLite di `/tmp` yang sementara; data bisa hilang.

## Struktur
```
app/
  __init__.py   application factory, CSRF
  db.py         koneksi SQLite, init-db, data demo
  auth.py       login, logout, ganti password, decorator peran
  admin.py      akun, keanggotaan, alat
  trainer.py    member, rencana latihan, progres
  member.py     dashboard member
  schema.sql    skema database
  templates/
public/         CSS, logo, favicon
index.py        titik masuk Vercel
tests/test_app.py
```

## Inspirasi
Konsep dan daftar fitur terinspirasi dari repo tugas kuliah EswarGitHub/GymManagementSystem. Kode ditulis ulang dari nol.
