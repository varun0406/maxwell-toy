#!/bin/bash
# Maxwell Accounting — Backend Startup Script

set -e

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting server..."
uvicorn app.main:app --host 0.0.0.0 --port 9833 --reload
