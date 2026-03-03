# Panduan Instalasi Secure-Link.Support

## Persyaratan Sistem

### Spesifikasi Server Minimum
- CPU: 2 core
- RAM: 4 GB
- Penyimpanan: 20 GB SSD
- OS: Ubuntu 20.04 LTS atau lebih baru

### Perangkat Lunak yang Diperlukan
- Docker Engine 20.10+ (opsional tetapi direkomendasikan)
- Docker Compose 1.29+ (opsional)
- Node.js 16.x
- Python 3.9+
- MongoDB 4.4+
- Redis 6.2+
- PostgreSQL 13+

## Prasyarat

Sebelum melakukan instalasi, pastikan Anda memiliki:
1. Nama domain yang mengarah ke IP server Anda
2. Sertifikat SSL (direkomendasikan Let's Encrypt)
3. Kunci API untuk:
   - Stripe (untuk pembayaran)
   - Midtrans (untuk pembayaran Indonesia)

## Langkah Instalasi

### 1. Mengkloning Repositori
```bash
# Kloning repositori
git clone https://github.com/your-repo/secure-link-support.git
cd secure-link-support
```

### 2. Konfigurasi Lingkungan

#### Backend (.env)
```env
# MongoDB
MONGO_URI=mongodb://localhost:27017/url_shortener

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=url_analytics
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=strong_password

# SQLite
SQLITE_DB_PATH=./analytics.db

# JWT
SECRET_KEY=your_super_secret_key_here_change_me

# Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Midtrans
MIDTRANS_IS_PRODUCTION=false
MIDTRANS_SERVER_KEY=your_midtrans_server_key
MIDTRANS_CLIENT_KEY=your_midtrans_client_key
```

#### Frontend (.env)
```env
VITE_API_URL=https://yourdomain.com/api
VITE_APP_NAME="Secure Link Support"
```

### 3. Pengaturan Basis Data

#### Inisialisasi MongoDB
```bash
# Memulai layanan MongoDB
sudo systemctl start mongod

# Membuat basis data dan pengguna
mongo <<EOF
use url_shortener
db.createUser({user: "app_user", pwd: "strong_password", roles: ["readWrite"]})
EOF
```

#### Inisialisasi PostgreSQL
```bash
# Memulai layanan PostgreSQL
sudo systemctl start postgresql

# Membuat basis data dan pengguna
sudo -u postgres psql <<EOF
CREATE DATABASE url_analytics;
CREATE USER analytics_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE url_analytics TO analytics_user;
EOF
```

### 4. Menginstal Dependensi

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

#### Frontend
```bash
cd ../frontend
npm install
```

### 5. Membangun Aplikasi

#### Membangun Frontend
```bash
# Membangun untuk produksi
npm run build
```

### 6. Mengonfigurasi Server Web (Nginx)

Buat `/etc/nginx/sites-available/secure-link-support`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Mengarahkan semua permintaan HTTP ke HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # Konfigurasi SSL
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/private.key;
    
    # Header Keamanan
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Kompresi Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;
    
    # File Statis
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Proxy API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Tantangan Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}
```

Aktifkan situs:
```bash
sudo ln -s /etc/nginx/sites-available/secure-link-support /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Mengatur Sertifikat SSL (Let's Encrypt)
```bash
# Menginstal Certbot
sudo apt install certbot python3-certbot-nginx

# Mendapatkan sertifikat
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 8. Manajemen Proses (PM2)

Instal PM2:
```bash
npm install -g pm2
```

Konfigurasi ekosistem backend (ecosystem.config.js):
```javascript
module.exports = {
  apps: [
    {
      name: 'secure-link-backend',
      script: 'server.py',
      interpreter: 'python3',
      cwd: '/path/to/backend',
      env: {
        NODE_ENV: 'production'
      }
    }
  ]
};
```

Memulai aplikasi:
```bash
# Memulai backend
cd /path/to/backend
pm2 start ecosystem.config.js

# Menyimpan daftar proses
pm2 save

# Menambahkan ke startup
pm2 startup
```

### 9. Petunjuk Deployment CyberPanel

Jika Anda menggunakan CyberPanel daripada deployment manual:

1. Buat situs web di CyberPanel dengan domain Anda
2. Akses manajer file situs web melalui CyberPanel
3. Unggah file build frontend ke direktori `public_html`
4. Unggah file backend ke direktori terpisah (misalnya, `/home/yourdomain/backend`)
5. Di CyberPanel, konfigurasikan subdirektori `/api` untuk mem-proxy permintaan ke backend Anda yang berjalan di port 8000
6. Siapkan basis data (MongoDB, Redis, PostgreSQL) melalui CyberPanel atau secara manual
7. Konfigurasikan variabel lingkungan di pengaturan aplikasi CyberPanel
8. Siapkan SSL melalui fungsi SSL CyberPanel

### 10. Konfigurasi Firewall
```bash
# Mengaktifkan UFW
sudo ufw enable

# Mengizinkan port yang diperlukan
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https

# Memeriksa status
sudo ufw status
```

## Memulai Aplikasi

1. Pastikan semua layanan berjalan:
   ```bash
   sudo systemctl start mongod
   sudo systemctl start redis-server
   sudo systemctl start postgresql
   ```

2. Mulai backend dengan PM2:
   ```bash
   cd /path/to/backend
   pm2 start ecosystem.config.js
   ```

3. Verifikasi konfigurasi Nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Pemantauan

### Log
```bash
# Log PM2
pm2 logs

# Log Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Log sistem
journalctl -u mongod
journalctl -u redis-server
journalctl -u postgresql
```

### Pemeriksaan Kesehatan
```bash
# Pemeriksaan kesehatan backend
curl https://yourdomain.com/api/health

# Koneksi basis data
mongo --eval "db.stats()"
sudo -u postgres psql -c "SELECT version();" url_analytics
```

## Strategi Cadangan

### Cadangan MongoDB
```bash
# Membuat direktori cadangan
mkdir -p /backups/mongodb

# Menjadwalkan cadangan harian
echo "0 2 * * * mongodump --out /backups/mongodb/$(date +\%Y\%m\%d)" | crontab -
```

### Cadangan PostgreSQL
```bash
# Membuat skrip cadangan
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +"%Y%m%d")
pg_dump url_analytics > "$BACKUP_DIR/analytics_$DATE.sql"

# Menjadwalkan cadangan harian
echo "0 3 * * * /path/to/pg_backup.sh" | crontab -
```

## Pemecahan Masalah

### Masalah Umum

1. **Aplikasi tidak dapat diakses**:
   - Periksa apakah semua layanan berjalan
   - Verifikasi konfigurasi Nginx
   - Periksa pengaturan firewall

2. **Kesalahan koneksi basis data**:
   - Verifikasi kredensial basis data
   - Periksa apakah layanan berjalan
   - Konfirmasi konektivitas jaringan

3. **Masalah pemrosesan pembayaran**:
   - Verifikasi kunci API
   - Periksa konfigurasi webhook
   - Tinjau dasbor penyedia pembayaran

### Prosedur Pemulihan

1. **Mengembalikan MongoDB dari cadangan**:
   ```bash
   # Menghentikan aplikasi
   pm2 stop all
   
   # Mengembalikan basis data
   mongorestore /backups/mongodb/YYYYMMDD
   
   # Memulai aplikasi
   pm2 start all
   ```

2. **Mengembalikan PostgreSQL dari cadangan**:
   ```bash
   # Menghentikan aplikasi
   pm2 stop all
   
   # Mengembalikan basis data
   sudo -u postgres psql url_analytics < /backups/postgresql/analytics_YYYYMMDD.sql
   
   # Memulai aplikasi
   pm2 start all
   ```

## Pemeliharaan

### Tugas Rutin

1. Perbarui paket sistem mingguan
2. Rotasi log bulanan
3. Tinjau sertifikat keamanan triwulanan
4. Uji cadangan bulanan

### Pembaruan

Untuk memperbarui aplikasi:
```bash
# Tarik kode terbaru
git pull origin main

# Perbarui dependensi
cd backend
pip install -r requirements.txt

cd ../frontend
npm install

# Bangun ulang frontend
npm run build

# Mulai ulang layanan
pm2 restart all
```
