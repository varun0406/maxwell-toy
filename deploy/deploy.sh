#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy/deploy.sh  — Run this on the server after each git pull
#
# Repo is at /root/maxwell-toy
# Usage:
#   cd /root/maxwell-toy && bash deploy/deploy.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

APP_DIR="/root/maxwell-toy"
cd "$APP_DIR"

echo "==> Pulling latest code..."
git pull origin main

echo "==> Installing/updating backend Python dependencies..."
backend/venv/bin/pip install -r backend/requirements.txt

echo "==> Restarting backend service (port 9833)..."
cp "$APP_DIR/deploy/maxwell-backend.service" /etc/systemd/system/maxwell-accounting.service
systemctl daemon-reload
systemctl restart maxwell-accounting

echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm ci --prefer-offline
npm run build

echo "==> Reloading nginx..."
systemctl reload nginx

echo ""
echo "✅ Deployed! Live at https://calculator.rovark.in"
