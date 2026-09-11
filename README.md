# Maxwell Mobile Accounting App 💼

A full-stack mobile accounting app built with **React + Capacitor (Android)** and **FastAPI + SQLite**.

---

## Project Structure

```
maxwellMobAcc/
├── backend/          ← FastAPI server
└── frontend/         ← React + Vite + Capacitor
```

---

## Backend — FastAPI

### First-time setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: http://localhost:8000/docs

### Deploy to your server

```bash
# On your server
sudo cp maxwell-accounting.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable maxwell-accounting
sudo systemctl start maxwell-accounting
```

### Environment variables (`.env` in `backend/`)

```env
SECRET_KEY=<generate with: openssl rand -hex 32>
DATABASE_URL=sqlite:///./maxwell_acc.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Frontend — React + Capacitor

### Setup

```bash
cd frontend
npm install
```

### Set your server URL

Edit `frontend/.env`:
```env
VITE_API_BASE_URL=http://YOUR_SERVER_IP:8000
```

### Run in browser (dev)

```bash
npm run dev
```

### Build and sync to Android

```bash
npm run build
npx cap sync android
npx cap open android        # Opens Android Studio
# OR
npx cap run android         # Run directly on connected device
```

### Install Capacitor (first time)

```bash
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap add android
```

---

## Features

| Feature | Details |
|---|---|
| **Authentication** | JWT access + refresh tokens, bcrypt passwords, rate-limited login |
| **Parties** | Create/edit/search customers, soft delete |
| **Invoices** | Auto-numbered, date-based, tracks balance_due |
| **Payments** | FIFO engine — oldest invoice cleared first |
| **FIFO Preview** | Live preview in payment form before saving |
| **Ledger** | Chronological per-party with running balance |
| **Analytics** | Bar chart, pie chart, aging report (0-30, 31-60, 61-90, 90+ days) |
| **Mobile UI** | Dark mode, bottom nav, pull-to-refresh, safe areas |

---

## FIFO Billing Logic

When a payment is recorded:
1. All unpaid invoices for the party are fetched, ordered by `invoice_date ASC`
2. Payment amount is applied to oldest invoice first
3. Each allocation is recorded in `payment_allocations` table
4. If payment exceeds all invoices, surplus is stored as `unallocated` (advance)

---

## Migrating from SQLite to PostgreSQL

1. Install `psycopg2-binary` and add to `requirements.txt`
2. Update `.env`: `DATABASE_URL=postgresql://user:pass@host/dbname`
3. Run `alembic upgrade head` (Alembic is included in `requirements.txt`)

---

## Android APK Build

1. Install Android Studio
2. `npm run build && npx cap sync android`
3. Open Android Studio → Build → Generate Signed APK
