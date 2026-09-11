#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy/deploy.sh  — Run this on the server after each git pull
#
# Assumes the repo is cloned to /var/www/maxwell
# Usage:
#   cd /var/www/maxwell && bash deploy/deploy.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

APP_DIR="/var/www/maxwell"
cd "$APP_DIR"

echo "==> Pulling latest code..."
git pull origin main

echo "==> Installing/updating backend Python dependencies..."
source venv/bin/activate
pip install -r backend/requirements.txt

echo "==> Restarting backend service (port 9833)..."
systemctl restart maxwell-accounting

echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm ci --prefer-offline
npm run build

echo "==> Reloading nginx..."
systemctl reload nginx

echo ""
echo "✅ Deployed! Live at https://calculator.rovark.in"
