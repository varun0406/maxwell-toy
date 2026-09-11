#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy/first_time_setup.sh
#
# Run ONCE on the server (git, npm, postgresql already installed).
# Assumes repo is already cloned to /var/www/maxwell
#
# Usage:  sudo bash deploy/first_time_setup.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

APP_DIR="/var/www/maxwell"
cd "$APP_DIR"

echo "==> Creating Python venv..."
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# ── Create backend .env ───────────────────────────────────────────────────────
if [ ! -f backend/.env ]; then
    echo "==> Creating backend .env..."
    SECRET=$(openssl rand -hex 32)
    cat > backend/.env <<EOF
DATABASE_URL=postgresql://maxwell:CHANGE_THIS_PASSWORD@localhost:5432/maxwell_acc
SECRET_KEY=$SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
APP_NAME=Maxwell Accounting
EOF
    echo "   --> Created backend/.env — EDIT IT and set a real DB password!"
else
    echo "   --> backend/.env already exists, skipping."
fi

# ── PostgreSQL: create DB + user ──────────────────────────────────────────────
echo "==> Setting up PostgreSQL database..."
sudo -u postgres psql <<SQL || echo "   (DB/user may already exist, continuing...)"
CREATE USER maxwell WITH PASSWORD 'CHANGE_THIS_PASSWORD';
CREATE DATABASE maxwell_acc OWNER maxwell;
GRANT ALL PRIVILEGES ON DATABASE maxwell_acc TO maxwell;
SQL

# ── Install systemd service ───────────────────────────────────────────────────
echo "==> Installing systemd service (port 9833)..."
cp deploy/maxwell-backend.service /etc/systemd/system/maxwell-accounting.service
systemctl daemon-reload
systemctl enable maxwell-accounting
systemctl start maxwell-accounting
sleep 2
systemctl status maxwell-accounting --no-pager

# ── Build frontend ────────────────────────────────────────────────────────────
echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm ci
npm run build

# ── Nginx ─────────────────────────────────────────────────────────────────────
echo "==> Installing Nginx config..."
cp "$APP_DIR/deploy/calculator.rovark.in" /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/calculator.rovark.in /etc/nginx/sites-enabled/

echo "==> Testing nginx config..."
nginx -t

echo "==> Reloading nginx..."
systemctl reload nginx

echo ""
echo "============================================================"
echo " First-time setup complete!"
echo ""
echo " IMPORTANT — Do these manually:"
echo "   1. Edit /var/www/maxwell/backend/.env"
echo "      Set a real DATABASE_URL password (and update postgres too)"
echo ""
echo "   2. Get SSL certificate:"
echo "      certbot --nginx -d calculator.rovark.in"
echo ""
echo "   3. Ensure DNS A record:"
echo "      calculator.rovark.in  ->  <this server's IP>"
echo "============================================================"
