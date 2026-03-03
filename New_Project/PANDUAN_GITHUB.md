# Panduan Menyimpan Kode Aplikasi di GitHub

GitHub adalah platform hosting kode berbasis Git yang sangat populer digunakan oleh developer untuk menyimpan, mengelola, dan berkolaborasi dalam proyek perangkat lunak. Berikut adalah langkah-langkah lengkap untuk menyimpan kode aplikasi secure-link.support Anda di GitHub.

## Persiapan Awal

### 1. Membuat Akun GitHub
Jika Anda belum memiliki akun GitHub:
1. Kunjungi [github.com](https://github.com)
2. Klik tombol "Sign up"
3. Masukkan username, email, dan password
4. Ikuti proses verifikasi

### 2. Menginstal Git di Komputer Lokal

Untuk Windows:
1. Download Git dari [git-scm.com](https://git-scm.com/downloads)
2. Jalankan installer dan ikuti petunjuk

Untuk macOS:
```bash
# Jika menggunakan Homebrew
brew install git

# Jika menggunakan MacPorts
port install git
```

Untuk Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install git
```

### 3. Konfigurasi Git
Setelah instalasi, konfigurasikan Git dengan identitas Anda:
```bash
git config --global user.name "Nama Lengkap Anda"
git config --global user.email "email@example.com"
```

## Membuat Repository di GitHub

1. Login ke akun GitHub Anda
2. Klik tombol "+" di pojok kanan atas
3. Pilih "New repository"
4. Beri nama repository (misal: secure-link-support)
5. Tambahkan deskripsi (opsional)
6. Pilih visibilitas (Public/Private)
7. Jangan inisialisasi dengan README.md (akan kita upload dari lokal)
8. Klik "Create repository"

## Mengupload Kode dari Komputer Lokal

### Metode 1: Menggunakan Command Line

1. Buka terminal/command prompt
2. Masuk ke direktori proyek Anda:
```bash
cd /path/ke/direktori/aplikasi/secure-link-support
```

3. Inisialisasi repository Git:
```bash
git init
```

4. Tambahkan semua file ke staging area:
```bash
git add .
```

5. Commit file:
```bash
git commit -m "Initial commit"
```

6. Tambahkan remote origin (ganti dengan URL repository Anda):
```bash
git remote add origin https://github.com/username-anda/secure-link-support.git
```

7. Push ke GitHub:
```bash
git branch -M main
git push -u origin main
```

### Metode 2: Menggunakan GitHub Desktop

1. Download dan instal [GitHub Desktop](https://desktop.github.com/)
2. Login dengan akun GitHub Anda
3. Klik "Choose a folder on your computer" dan pilih direktori proyek
4. Klik "Create a repository"
5. Isi nama repository dan deskripsi
6. Klik "Commit to main"
7. Klik "Publish repository" untuk mengupload ke GitHub

## Struktur Repository yang Disarankan

Untuk aplikasi secure-link.support, struktur repository yang baik:
```
secure-link-support/
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── docs/
│   ├── INSTALLATION_GUIDE.md
│   └── ...
├── .gitignore
├── README.md
└── LICENSE
```

## File Penting yang Harus Ada

### 1. README.md
File dokumentasi utama proyek Anda. Contoh isi:
```markdown
# Secure Link Support

Aplikasi URL shortener dengan fitur advanced analytics dan monetisasi.

## Fitur Utama
- Shortlink dengan custom domain
- Analytics real-time
- Country targeting
- Proteksi bot
- Sistem pembayaran (Stripe & Midtrans)

## Instalasi
Lihat [INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md)

## Lisensi
MIT License
```

### 2. .gitignore
File untuk mengecualikan file sensitif dari repository:
```
# Environment variables
.env

# Database
*.db

# Logs
*.log

# Node modules
node_modules/

# Python
__pycache__/
*.pyc

# IDE
.vscode/
.idea/
```

### 3. LICENSE
File lisensi proyek Anda (misal MIT License).

## Best Practices

1. **Commit Secara Teratur**: Buat commit kecil dan deskriptif
2. **Branching**: Gunakan branch untuk fitur baru
3. **Pull Request**: Untuk kolaborasi tim
4. **Issue Tracking**: Gunakan fitur Issues di GitHub
5. **Release Tags**: Tandai versi stabil dengan tag

## Troubleshooting

### Masalah Umum

1. **Permission Denied**:
   - Pastikan Anda menggunakan HTTPS atau SSH dengan kredensial yang benar
   - Cek credential helper: `git config --global credential.helper`

2. **Merge Conflicts**:
   - Selesaikan konflik secara manual
   - Gunakan `git status` untuk melihat file yang bermasalah

3. **Large Files**:
   - Untuk file besar (>100MB), gunakan Git LFS
   - Install Git LFS: `git lfs install`

### Tips Keamanan

1. Jangan pernah menyimpan:
   - API keys
   - Password
   - File konfigurasi sensitif

2. Gunakan environment variables dan file .env
3. Tambahkan .env ke .gitignore

## Kolaborasi Tim

1. **Fork Repository**: Untuk kontributor eksternal
2. **Branch Protection**: Lindungi branch penting
3. **Code Review**: Gunakan Pull Request untuk review kode
4. **CI/CD**: Integrasikan dengan GitHub Actions

Dengan mengikuti panduan ini, kode aplikasi secure-link.support Anda akan tersimpan dengan aman di GitHub dan siap untuk pengembangan lebih lanjut serta kolaborasi tim.
