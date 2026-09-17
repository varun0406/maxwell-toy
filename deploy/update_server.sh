#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy/update_server.sh
# Update script for Maxwell Accounting
#
# Run this on the server as root (or use sudo):
#   cd /var/www/maxwell && sudo bash deploy/update_server.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

APP_DIR="/var/www/maxwell"

if [ ! -d "$APP_DIR" ]; then
    echo "Error: Directory $APP_DIR does not exist."
    echo "Are you running this on the server where the app is deployed?"
    exit 1
fi

echo "==> Navigating to app directory..."
cd "$APP_DIR"

echo "==> Pulling latest changes from git..."
git pull

echo "==> Updating Python backend dependencies..."
source venv/bin/activate
pip install -r backend/requirements.txt

echo "==> Rebuilding frontend..."
cd "$APP_DIR/frontend"
npm install
npm run build
cd "$APP_DIR"

echo "==> Updating Nginx config (if changed)..."
cp "$APP_DIR/deploy/calculator.rovark.in" /etc/nginx/sites-available/
nginx -t

echo "==> Restarting services..."
systemctl restart maxwell-backend
systemctl reload nginx

echo ""
echo "============================================================"
echo " Server update complete!"
echo "============================================================"
