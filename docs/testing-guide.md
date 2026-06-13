# End-to-End Testing Guide

This guide walks through everything needed to run and test the full stack:
**FastAPI backend** (auth, RAG chat, scraper) + **Next.js frontend** (login, register, chat, admin panel).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Step 0 — Build databases (new environment)](#2-step-0--build-databases-new-environment)
3. [Step 1 — Configure environment variables](#3-step-1--configure-environment-variables)
4. [Step 2 — Start the FastAPI backend](#4-step-2--start-the-fastapi-backend)
5. [Step 3 — Seed the super admin (one-time)](#5-step-3--seed-the-super-admin-one-time)
6. [Step 4 — Install and start the Next.js frontend](#6-step-4--install-and-start-the-nextjs-frontend)
7. [Step 5 — Full user flow walkthrough](#7-step-5--full-user-flow-walkthrough)
8. [Step 6 — Admin panel walkthrough](#8-step-6--admin-panel-walkthrough)
9. [Step 7 — Testing the chat API directly with curl](#9-step-7--testing-the-chat-api-directly-with-curl)
10. [Step 8 — Testing the auth API with curl](#10-step-8--testing-the-auth-api-with-curl)
11. [Common errors and fixes](#11-common-errors-and-fixes)

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.11 | [python.org](https://python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | ≥ 18 | [nodejs.org](https://nodejs.org) |
| npm | ≥ 9 | bundled with Node.js |

---

## 2. Step 0 — Build databases (new environment)

> **Skip this section if you already have `preprocessed_db/` populated.**
> Both database files (`preprocessed_db/` and `auth.db`) are git-ignored and must be
> created locally on every fresh clone.

There are **two databases** this project needs:

| Database | File | Created by |
|----------|------|------------|
| Auth DB (SQLite) | `auth.db` | Auto-created on first backend startup |
| Vector DB (ChromaDB) | `preprocessed_db/` | Built by running the scrape → ingest pipeline |

---

### 2a. Auth database — automatic

`auth.db` is created automatically when the FastAPI backend starts for the first time.
No action required — just follow Step 2 onward.

---

### 2b. Vector database — build from scratch

The knowledge base must be crawled and ingested before the chat endpoint will work.
This is a two-step process: **scrape** the site into markdown files, then **ingest** them into ChromaDB.

**Prerequisites for this step:**
- Backend must be running (Step 2)
- `ADMIN_API_KEY` must be set in `.env` (Step 1)
- Playwright browsers installed:

```bash
uv run playwright install chromium
```

#### Step 1 — Start the crawler

```bash
curl -X POST http://localhost:8000/api/scrape/start \
  -H "X-API-Key: <your-ADMIN_API_KEY>"
```

Expected response:
```json
{"status": "started", "message": "Crawl started in background."}
```

#### Step 2 — Poll until crawl is complete

```bash
curl http://localhost:8000/api/scrape/status \
  -H "X-API-Key: <your-ADMIN_API_KEY>"
```

Keep polling until `running` becomes `false`. A full crawl typically takes **5–15 minutes** depending on site size.

```json
{
  "running": false,
  "pages_crawled": 312,
  "categories": {"services": 45, "blog": 120, ...}
}
```

#### Step 3 — Run ingestion (builds the ChromaDB vector store)

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "X-API-Key: <your-ADMIN_API_KEY>"
```

Expected response:
```json
{"status": "started", "message": "Ingestion pipeline running in background."}
```

Poll until done (ingestion takes **2–10 minutes**):

```bash
curl http://localhost:8000/api/ingest/status \
  -H "X-API-Key: <your-ADMIN_API_KEY>"
```

```json
{"running": false, "last_run": "2024-01-15T10:30:00"}
```

#### One-shot alternative — scrape + ingest in a single call

```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "X-API-Key: <your-ADMIN_API_KEY>"
```

This runs both steps sequentially in the background. Poll `/api/ingest/status` to know when it's done.

#### Verify the vector DB was built

```bash
ls -lh preprocessed_db/
# Should show: chroma.sqlite3 (~50–100 MB) and a UUID folder
```

Once `preprocessed_db/` exists and is populated, the chat endpoint (`/api/chat`) will work.

---

## 3. Step 1 — Configure environment variables

### Backend `.env`

The backend `.env` already exists. Open it and confirm or update these values:

```env
# /Users/siddhanttrivedi/Desktop/Production RAG Course/radixweb-kb-crawl-v1/.env

OPENAI_API_KEY=sk-...            # your real OpenAI key
ADMIN_API_KEY=change-me-before-deploying   # used for /api/scrape and /api/ingest

# ── NEW — Required for RBAC auth module ──
AUTH_JWT_SECRET=my-super-secret-key-at-least-32-characters
```

> **Critical:** `AUTH_JWT_SECRET` must be at least 32 characters and kept secret.
> Use `openssl rand -hex 32` to generate a strong random secret.

```bash
openssl rand -hex 32
# example output: a3f8d2c1e5b7a9f0c2d4e6b8a0f2c4d6e8b0a2c4d6e8b0a2c4d6e8b0a2c4d6
```

### Frontend `.env.local`

```bash
cd frontend
cp .env.local.example .env.local
```

Edit `frontend/.env.local`:

```env
# URL of the FastAPI backend — server-side only (not exposed to browser)
API_BASE_URL=http://localhost:8000

# MUST be exactly the same value as AUTH_JWT_SECRET in the backend .env
AUTH_JWT_SECRET=my-super-secret-key-at-least-32-characters
```

---

## 4. Step 2 — Start the FastAPI backend

From the **project root**:

```bash
# Install/sync dependencies (if not done yet)
uv sync

# Start the server
uv run uvicorn api:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
Scheduler started — hourly ingestion configured.
```

Verify it's working:
```bash
curl http://localhost:8000/docs
# Should return HTML — open in browser for Swagger UI
```

---

## 5. Step 3 — Seed the super admin *(one-time)*

This creates the first super admin account. **Only works once** — subsequent calls return `409 Conflict`.

```bash
curl -X POST http://localhost:8000/auth/admin/init \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@radixweb.com",
    "full_name": "Super Admin",
    "password": "AdminPass123!"
  }'
```

Expected response:
```json
{
  "id": 1,
  "email": "admin@radixweb.com",
  "full_name": "Super Admin",
  "role": "super_admin",
  "status": "approved",
  "created_at": "2024-01-15T10:00:00"
}
```

> Save the email and password — you'll need them to log into the admin panel.

---

## 6. Step 4 — Install and start the Next.js frontend

```bash
cd frontend
npm install
npm run dev
```

Expected output:
```
  ▲ Next.js 14.2.5
  - Local:        http://localhost:3000
  - Environments: .env.local
  ✓ Ready in 2.1s
```

Open **http://localhost:3000** in your browser — you'll be redirected to `/login`.

---

## 7. Step 5 — Full user flow walkthrough

### 5a. Register a regular user

1. Go to **http://localhost:3000/register**
2. Fill in: Full name, Email (`user@example.com`), Password (`TestPass123!`)
3. Click **Create account**
4. You see: *"Account created! Your account is pending approval."*

### 5b. Try to log in as the pending user (should fail)

1. Go to **http://localhost:3000/login**
2. Enter `user@example.com` / `TestPass123!`
3. You see: *"Your account is pending approval by a super admin."*

### 5c. Log in as super admin and approve

1. Log in with `admin@radixweb.com` / `AdminPass123!`
2. You're redirected to `/admin` (the admin panel)
3. Find the user in the **Pending** tab
4. Click **Approve**
5. The status badge changes to **approved**

### 5d. Log in as the approved user

1. Open an incognito tab or log out
2. Go to **http://localhost:3000/login**
3. Enter `user@example.com` / `TestPass123!`
4. You're redirected to `/chat` ✓

### 5e. Use the chat

1. Type a question: *"What services does Radixweb offer?"*
2. Press **Enter** or click the send button
3. You see the typing indicator (three bouncing dots)
4. The answer appears with a **Sources** accordion below it
5. Expand sources to see the knowledge base chunks used

---

## 8. Step 6 — Admin panel walkthrough

Log in as the super admin, you land on `/admin`.

### Stats bar
Shows total users and counts per status at the top.

### Filter tabs
Click **Pending**, **Approved**, **Denied**, **Revoked** to filter the user table.

### Actions per user status

| Status | Available actions |
|--------|-------------------|
| `pending` | Approve, Deny (requires reason) |
| `approved` | Revoke, Make Admin / Remove Admin |
| `denied` | Approve, Delete |
| `revoked` | Approve, Delete |

### Deny a user
1. Click **Deny** on a pending user
2. A modal appears — enter a reason (min 5 chars): *"Not a registered employee."*
3. Click **Deny access**
4. The denial reason is stored and shown in the table

### Promote a user to admin
1. Find an approved user
2. Click **Make Admin**
3. Their role badge changes to **Super Admin**
4. They can now log in and access `/admin`

---

## 9. Step 7 — Testing the chat API directly with curl

### Get a token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"TestPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

### Send a chat message

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "What does Radixweb specialize in?",
    "history": []
  }'
```

Expected response shape:
```json
{
  "answer": "Radixweb specializes in...",
  "sources": [
    {
      "page_content": "...",
      "metadata": { "source": "/path/to/file.md", "type": "services" }
    }
  ]
}
```

### Multi-turn conversation

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "Can you tell me more about their mobile development services?",
    "history": [
      {"role": "user", "content": "What does Radixweb specialize in?"},
      {"role": "assistant", "content": "Radixweb specializes in..."}
    ]
  }'
```

### Verify token (used by Next.js middleware)

```bash
curl -X POST http://localhost:8000/api/chat/verify \
  -H "Authorization: Bearer $TOKEN"
```

---

## 10. Step 8 — Testing the auth API with curl

### Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","full_name":"New User","password":"NewPass123!"}'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@radixweb.com","password":"AdminPass123!"}'
```

### List all pending users (admin)

```bash
curl "http://localhost:8000/auth/admin/users?status=pending" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Approve a user (replace 2 with the real user ID)

```bash
curl -X PATCH http://localhost:8000/auth/admin/users/2/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Deny a user with reason

```bash
curl -X PATCH http://localhost:8000/auth/admin/users/2/deny \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Unrecognised email domain — not a Radixweb employee."}'
```

### Get user stats

```bash
curl http://localhost:8000/auth/admin/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 11. Common errors and fixes

### `AUTH_JWT_SECRET is not set`
The frontend middleware logs this if `AUTH_JWT_SECRET` is missing in `frontend/.env.local`.
**Fix:** add `AUTH_JWT_SECRET=<same-value-as-backend>` to `frontend/.env.local` and restart `npm run dev`.

### `401 Invalid or expired token`
The JWT has expired (default 24 h) or the secrets don't match.
**Fix:** log out and log in again. If it keeps happening, ensure both `.env` files have the same `AUTH_JWT_SECRET`.

### `503 RAG backend is not available`
The `pro_implementation` module failed to import (usually missing `bm25_index.pkl` or `preprocessed_db/`).
**Fix:** run the ingestion pipeline first:
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "X-API-Key: change-me-before-deploying"
```
Then poll until done:
```bash
curl http://localhost:8000/api/ingest/status
```

### `409 A super admin already exists`
`POST /auth/admin/init` was already called.
**Fix:** just log in with the credentials you used during init.

### `CORS error` in the browser
The frontend calls its own Next.js API routes (not the FastAPI server directly), so CORS is not an issue in normal operation. If you're calling the FastAPI server directly from the browser during testing, add the frontend origin to the FastAPI CORS config.

### Next.js middleware redirect loop
Usually means `AUTH_JWT_SECRET` in the frontend doesn't match the backend — tokens fail to verify, middleware redirects to `/login`, which is public, so no loop, but you can never log in.
**Fix:** confirm both secrets are identical (copy-paste, no trailing spaces).

### `Cannot approve a super admin account`
You are trying to approve/revoke/deny the same super_admin account you used to call the endpoint.
**Fix:** use a different super admin to manage the target account, or promote a regular user to super_admin first.

---

## Quick reference — ports and URLs

| Service | URL |
|---------|-----|
| FastAPI backend | http://localhost:8000 |
| FastAPI Swagger UI | http://localhost:8000/docs |
| Gradio chat UI (protected) | http://localhost:8000/ |
| Next.js frontend | http://localhost:3000 |
| Login page | http://localhost:3000/login |
| Register page | http://localhost:3000/register |
| Chat page | http://localhost:3000/chat |
| Admin panel | http://localhost:3000/admin |
