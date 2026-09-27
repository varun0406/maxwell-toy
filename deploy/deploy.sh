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

echo "==> Installing backend service definition..."
cp "$APP_DIR/deploy/maxwell-backend.service" /etc/systemd/system/maxwell-accounting.service
systemctl daemon-reload

echo "==> Building frontend..."
cd "$APP_DIR/frontend"
npm ci --prefer-offline
npm run build

echo "==> Validating and installing nginx config..."
cp "$APP_DIR/deploy/calculator.rovark.in" /etc/nginx/sites-available/calculator.rovark.in
ln -sf /etc/nginx/sites-available/calculator.rovark.in /etc/nginx/sites-enabled/calculator.rovark.in
nginx -t

echo "==> Restarting backend and reloading nginx..."
systemctl restart maxwell-accounting
systemctl reload nginx

echo ""
echo "✅ Deployed! Live at https://calculator.rovark.in"
