#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# Run this on the server (as root) — server already has git/npm/postgres/venv
#
# cd ~/maxwell-toy && bash deploy/server_init.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> App dir: $APP_DIR"

# ── Install backend deps in existing venv ─────────────────────────────────────
echo "==> Installing Python dependencies..."
cd "$APP_DIR/backend"
source "$APP_DIR/backend/venv/bin/activate" 2>/dev/null || source "$APP_DIR/venv/bin/activate"
pip install -r requirements.txt

# ── Run DB migrations (create tables if not exist) ────────────────────────────
echo "==> Creating DB tables..."
cd "$APP_DIR/backend"
python3 -c "
from app.database import engine, Base
import app.models
Base.metadata.create_all(bind=engine)
print('Tables created / already exist.')
"

# ── Install systemd service (port 9833) ───────────────────────────────────────
echo "==> Installing systemd service..."

# Detect venv location
VENV_PATH=$(which uvicorn | sed 's|/bin/uvicorn||')
echo "   venv path: $VENV_PATH"

cat > /etc/systemd/system/maxwell-accounting.service <<EOF
[Unit]
Description=Maxwell Accounting FastAPI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/backend/.env
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/uvicorn app.main:app --host 127.0.0.1 --port 9833 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable maxwell-accounting
systemctl restart maxwell-accounting
sleep 2
echo "==> Backend status:"
systemctl status maxwell-accounting --no-pager | head -15

# ── Build frontend ────────────────────────────────────────────────────────────
echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm ci --prefer-offline 2>/dev/null || npm install
npm run build
echo "   Frontend built to: $APP_DIR/frontend/dist"

# ── Install Nginx config ──────────────────────────────────────────────────────
echo "==> Installing Nginx config..."
DIST_PATH="$APP_DIR/frontend/dist"

# Patch the nginx config root path to match actual location
sed "s|/var/www/maxwell/frontend/dist|$DIST_PATH|g" \
    "$APP_DIR/deploy/calculator.rovark.in" \
    > /etc/nginx/sites-available/calculator.rovark.in

ln -sf /etc/nginx/sites-available/calculator.rovark.in \
       /etc/nginx/sites-enabled/calculator.rovark.in

echo "==> Testing nginx..."
nginx -t && systemctl reload nginx

echo ""
echo "============================================================"
echo " Setup complete!"
echo ""
echo " Backend running on: http://127.0.0.1:9833"
echo " Frontend dist at:   $DIST_PATH"
echo " Nginx config at:    /etc/nginx/sites-available/calculator.rovark.in"
echo ""
echo " NEXT STEPS:"
echo "   1. Point DNS A record: calculator.rovark.in -> $(curl -s ifconfig.me)"
echo "   2. Get SSL:  certbot --nginx -d calculator.rovark.in"
echo "   3. Test API: curl http://127.0.0.1:9833/docs"
echo "============================================================"
