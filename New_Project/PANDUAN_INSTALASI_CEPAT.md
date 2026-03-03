# Panduan Instalasi Cepat Secure-Link.Support

Ikuti langkah-langkah berikut untuk menginstal aplikasi dengan cepat dan mudah.

## Prasyarat

Pastikan server Anda memenuhi spesifikasi berikut:
- Ubuntu 20.04+ atau CentOS 8+
- RAM minimal 4GB
- Ruang disk 20GB+
- Akses root atau sudo

## Instalasi Otomatis

1. Unduh script instalasi:
   ```bash
   wget https://raw.githubusercontent.com/secure-link-support/installer/main/install.sh
   chmod +x install.sh
   ```

2. Jalankan instalasi:
   ```bash
   ./install.sh
   ```

3. Ikuti petunjuk di layar untuk konfigurasi awal.

## Instalasi Manual (CyberPanel)

1. Buat website baru di CyberPanel
2. Akses File Manager melalui CyberPanel
3. Upload file frontend ke direktori `public_html`
4. Upload file backend ke `/home/domainanda/backend`
5. Konfigurasikan Proxy di CyberPanel:
   - Path: `/api`
   - Target: `http://localhost:8000`
6. Impor database dari file `.sql` yang disediakan
7. Sesuaikan file `.env` di direktori backend
8. Restart services melalui CyberPanel

## Konfigurasi Awal

1. Akses admin panel di: `https://domainanda.com/admin`
2. Login dengan kredensial default:
   - Email: admin@secure-link.support
   - Password: admin123456
3. Ubah password admin segera setelah login
4. Konfigurasikan pengaturan pembayaran di halaman Admin

## Verifikasi Instalasi

Setelah instalasi selesai, verifikasi dengan:
1. Membuka homepage di browser
2. Mencoba membuat akun pengguna baru
3. Membuat shortlink percobaan
4. Memastikan halaman analitik menampilkan data

## Bantuan

Jika mengalami masalah:
- Periksa log error di `/var/log/secure-link/`
- Pastikan semua services berjalan dengan `systemctl status`
- Hubungi tim support jika masalah berlanjut
