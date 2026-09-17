#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy/update_server.sh
# Update script for Maxwell Accounting
#
# Run this on the server as root:
#   cd /root/maxwell-toy && bash deploy/update_server.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

# Get the directory where the app is located (parent of deploy directory)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d "$APP_DIR/.git" ]; then
    echo "Error: Directory $APP_DIR is not a git repository."
    echo "Please run this script from inside the git repository."
    exit 1
fi

echo "==> Navigating to app directory..."
cd "$APP_DIR"

echo "==> Pulling latest changes from git..."
git pull

echo "==> Updating Python backend dependencies..."
venv/bin/pip install -r backend/requirements.txt

echo "==> Rebuilding frontend..."
cd "$APP_DIR/frontend"
npm install
npm run build
cd "$APP_DIR"

echo "==> Updating Nginx config (if changed)..."
cp "$APP_DIR/deploy/calculator.rovark.in" /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/calculator.rovark.in /etc/nginx/sites-enabled/
nginx -t

echo "==> Restarting services..."
cp "$APP_DIR/deploy/maxwell-backend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl restart maxwell-backend
systemctl reload nginx

echo ""
echo "============================================================"
echo " Server update complete!"
echo "============================================================"
