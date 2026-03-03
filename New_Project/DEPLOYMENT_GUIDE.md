# Secure-Link.Support Deployment Guide

## System Requirements

### Minimum Server Specifications
- CPU: 2 cores
- RAM: 4 GB
- Storage: 20 GB SSD
- OS: Ubuntu 20.04 LTS or newer

### Required Software
- Docker Engine 20.10+
- Docker Compose 1.29+
- Node.js 16.x
- Python 3.9+
- MongoDB 4.4+
- Redis 6.2+
- PostgreSQL 13+

## Prerequisites

Before deploying, ensure you have:
1. Domain name pointing to your server IP
2. SSL certificate (Let's Encrypt recommended)
3. API keys for:
   - Stripe (for payments)
   - Midtrans (for Indonesian payments)
   - IP-API (for geolocation)

## Installation Steps

### 1. Clone Repository
```bash
# Clone the repository
git clone https://github.com/your-repo/secure-link-support.git
cd secure-link-support
```

### 2. Environment Configuration

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

### 3. Database Setup

#### MongoDB Initialization
```bash
# Start MongoDB service
sudo systemctl start mongod

# Create database and user
mongo <<EOF
use url_shortener
db.createUser({user: "app_user", pwd: "strong_password", roles: ["readWrite"]})
EOF
```

#### PostgreSQL Initialization
```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE url_analytics;
CREATE USER analytics_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE url_analytics TO analytics_user;
EOF
```

### 4. Install Dependencies

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

### 5. Build Application

#### Frontend Build
```bash
# Build for production
npm run build
```

### 6. Configure Web Server (Nginx)

Create `/etc/nginx/sites-available/secure-link-support`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/private.key;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;
    
    # Static Files
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API Proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Let's Encrypt Challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/secure-link-support /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Setup SSL Certificate (Let's Encrypt)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 8. Process Management (PM2)

Install PM2:
```bash
npm install -g pm2
```

Backend ecosystem.config.js:
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

Start applications:
```bash
# Start backend
cd /path/to/backend
pm2 start ecosystem.config.js

# Save process list
pm2 save

# Add to startup
pm2 startup
```

### 9. CyberPanel Deployment Instructions

If you're using CyberPanel instead of manual deployment:

1. Create a website in CyberPanel with your domain
2. Access the website's file manager through CyberPanel
3. Upload the frontend build files to `public_html` directory
4. Upload backend files to a separate directory (e.g., `/home/yourdomain/backend`)
5. In CyberPanel, configure the subdirectory `/api` to proxy requests to your backend running on port 8000
6. Set up the databases (MongoDB, Redis, PostgreSQL) through CyberPanel or manually
7. Configure environment variables in CyberPanel's application settings
8. Set up SSL through CyberPanel's SSL functionality

### 10. Firewall Configuration
```bash
# Enable UFW
sudo ufw enable

# Allow required ports
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https

# Check status
sudo ufw status
```

## Starting the Application

1. Ensure all services are running:
   ```bash
   sudo systemctl start mongod
   sudo systemctl start redis-server
   sudo systemctl start postgresql
   ```

2. Start backend with PM2:
   ```bash
   cd /path/to/backend
   pm2 start ecosystem.config.js
   ```

3. Verify Nginx configuration:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Monitoring

### Logs
```bash
# PM2 logs
pm2 logs

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# System logs
journalctl -u mongod
journalctl -u redis-server
journalctl -u postgresql
```

### Health Checks
```bash
# Backend health check
curl https://yourdomain.com/api/health

# Database connections
mongo --eval "db.stats()"
sudo -u postgres psql -c "SELECT version();" url_analytics
```

## Backup Strategy

### MongoDB Backup
```bash
# Create backup directory
mkdir -p /backups/mongodb

# Schedule daily backup
echo "0 2 * * * mongodump --out /backups/mongodb/$(date +\%Y\%m\%d)" | crontab -
```

### PostgreSQL Backup
```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +"%Y%m%d")
pg_dump url_analytics > "$BACKUP_DIR/analytics_$DATE.sql"

# Schedule daily backup
echo "0 3 * * * /path/to/pg_backup.sh" | crontab -
```

## Troubleshooting

### Common Issues

1. **Application not accessible**:
   - Check if all services are running
   - Verify Nginx configuration
   - Check firewall settings

2. **Database connection errors**:
   - Verify database credentials
   - Check if services are running
   - Confirm network connectivity

3. **Payment processing issues**:
   - Verify API keys
   - Check webhook configurations
   - Review payment provider dashboards

### Recovery Procedures

1. **Restore MongoDB from backup**:
   ```bash
   # Stop application
   pm2 stop all
   
   # Restore database
   mongorestore /backups/mongodb/YYYYMMDD
   
   # Start application
   pm2 start all
   ```

2. **Restore PostgreSQL from backup**:
   ```bash
   # Stop application
   pm2 stop all
   
   # Restore database
   sudo -u postgres psql url_analytics < /backups/postgresql/analytics_YYYYMMDD.sql
   
   # Start application
   pm2 start all
   ```

## Maintenance

### Regular Tasks

1. Update system packages weekly
2. Rotate logs monthly
3. Review security certificates quarterly
4. Test backups monthly

### Updates

To update the application:
```bash
# Pull latest code
git pull origin main

# Update dependencies
cd backend
pip install -r requirements.txt

cd ../frontend
npm install

# Rebuild frontend
npm run build

# Restart services
pm2 restart all
```
