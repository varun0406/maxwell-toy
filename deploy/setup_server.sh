#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy/setup_server.sh
# One-time server setup script for Maxwell Accounting
#
# Run this on a fresh Ubuntu 22.04/24.04 server as root:
#   chmod +x setup_server.sh && sudo bash setup_server.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

APP_DIR="/root/maxwell-toy"
FRONTEND_DIR="$APP_DIR/frontend"
SERVICE_USER="root"

echo "==> Updating packages..."
apt-get update && apt-get install -y \
    git nginx python3 python3-pip python3-venv \
    postgresql postgresql-contrib \
    certbot python3-certbot-nginx \
    curl

echo "==> Creating app directory..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "==> Cloning repo..."
git clone https://github.com/varun0406/maxwell-toy.git .
# NOTE: If already cloned (e.g. at /root/maxwell-toy), skip this step.

echo "==> Setting up Python venv..."
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

echo "==> Setting up .env for backend..."
cat > backend/.env <<EOF
DATABASE_URL=postgresql://maxwell:CHANGE_PASSWORD@localhost:5432/maxwell_acc
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
APP_NAME=Maxwell Accounting
EOF
echo "   --> backend/.env created. Set your DATABASE_URL password!"

echo "==> Setting up PostgreSQL..."
sudo -u postgres psql <<SQL
CREATE USER maxwell WITH PASSWORD 'CHANGE_PASSWORD';
CREATE DATABASE maxwell_acc OWNER maxwell;
SQL

echo "==> Installing Node.js (via nvm)..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm install
# .env.production is already committed — it points to https://calculator.rovark.in/api
npm run build

echo "==> Installing Nginx config..."
cp "$APP_DIR/deploy/calculator.rovark.in" /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/calculator.rovark.in /etc/nginx/sites-enabled/
nginx -t

echo "==> Copying backend systemd service..."
cp "$APP_DIR/deploy/maxwell-backend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable maxwell-backend
systemctl start maxwell-backend

echo "==> Reloading Nginx..."
systemctl reload nginx

echo ""
echo "============================================================"
echo " Server setup complete!"
echo " Next steps:"
echo "   1. Edit /root/maxwell-toy/backend/.env — set a real DB password"
echo "   2. Run: certbot --nginx -d calculator.rovark.in"
echo "   3. Ensure DNS A record: calculator.rovark.in -> this server's IP"
echo "============================================================"
