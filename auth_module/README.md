# Auth Module — RBAC for Radixweb RAG System

Self-contained FastAPI module that adds **role-based access control** to the Radixweb knowledge base chatbot. Users register, a super admin approves or denies them, and only approved accounts can access the Gradio UI or call the chatbot REST API from Next.js.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Folder Structure](#folder-structure)
3. [Roles and User Lifecycle](#roles-and-user-lifecycle)
4. [Environment Variables](#environment-variables)
5. [First-Time Setup](#first-time-setup)
6. [API Reference](#api-reference)
7. [Next.js Integration](#nextjs-integration)
8. [Gradio Integration](#gradio-integration)
9. [Running as a Standalone Service](#running-as-a-standalone-service)
10. [Security Notes](#security-notes)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      api.py (main app)                  │
│                                                         │
│  /auth/*   ← auth_module (register, login, admin)       │
│  /api/chat ← auth_module (protected RAG endpoint)       │
│  /         ← Gradio UI  (guarded by gradio_auth)        │
└─────────────────────────────────────────────────────────┘
         ↑                              ↑
    Next.js UI                    Browser / Gradio
  (JWT Bearer)                  (email + password)
```

**Database:** SQLite (`auth_module/auth.db`) via SQLAlchemy — zero external database setup required.  
**Auth:** JWT HS256 signed with `AUTH_JWT_SECRET`, valid for 24 hours by default.  
**Passwords:** bcrypt via passlib.

---

## Folder Structure

```
auth_module/
├── __init__.py          # Convenient re-exports for api.py integration
├── app.py               # Standalone FastAPI app (can run independently)
├── config.py            # Settings from environment variables
├── database.py          # SQLAlchemy engine, session, create_tables()
├── models.py            # User ORM model, UserRole enum, UserStatus enum
├── schemas.py           # Pydantic v2 request / response schemas
├── security.py          # bcrypt password hashing + JWT create/decode
├── dependencies.py      # FastAPI dependency injectors (get_current_user, etc.)
├── gradio_auth.py       # Gradio auth callback (plugs into gr.mount_gradio_app)
├── routers/
│   ├── auth.py          # /auth/register, /auth/login, /auth/me, /auth/admin/init
│   ├── admin.py         # /auth/admin/users/* (super admin only)
│   └── chat.py          # /api/chat, /api/chat/verify
└── README.md            # This file
```

---

## Roles and User Lifecycle

### Roles

| Role          | Description                                                    |
| ------------- | -------------------------------------------------------------- |
| `user`        | Default role. Access Gradio UI and chatbot API after approval. |
| `super_admin` | Manage all user accounts. Access everything a `user` can.      |

### Status Flow

```
register()          approve()           revoke()
  PENDING ──────────► APPROVED ─────────► REVOKED
          │
          └──────────► DENIED  (by super admin with a reason)
```

Only `APPROVED` accounts can log in and use the system.

---

## Environment Variables

Add to your `.env` file:

```env
# JWT signing secret — change this before deploying!
AUTH_JWT_SECRET=your-super-secret-key-at-least-32-characters

# Optional (these are the defaults)
AUTH_JWT_ALGORITHM=HS256
AUTH_TOKEN_EXPIRE_MINUTES=1440
AUTH_DATABASE_URL=sqlite:///./auth_module/auth.db
```

---

## First-Time Setup

After first deployment, bootstrap the super admin account **once**:

```bash
curl -X POST http://localhost:8000/auth/admin/init \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@radixweb.com",
    "full_name": "Super Admin",
    "password": "Radixweb@123!"
  }'
```

This endpoint returns `409 Conflict` on any subsequent call, so it is safe to leave it enabled.

---

## API Reference

### Authentication

#### `POST /auth/register`

Create a new account (status = `pending`).

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "full_name": "Jane Doe", "password": "MyPass123!"}'
```

Response:

```json
{
    "id": 2,
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "role": "user",
    "status": "pending",
    "created_at": "2024-01-15T10:30:00"
}
```

#### `POST /auth/login`

Exchange credentials for a JWT. Only works for `approved` accounts.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "MyPass123!"}'
```

Response:

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": { "id": 2, "email": "...", "role": "user", "status": "approved", ... }
}
```

#### `GET /auth/me`

Get your own profile.

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

#### `POST /auth/token/verify`

Validate a token — used by Next.js middleware.

```bash
curl -X POST http://localhost:8000/auth/token/verify \
  -H "Authorization: Bearer <token>"
```

---

### Admin — User Management

All admin endpoints require a super admin JWT.

#### `GET /auth/admin/users`

List all users (supports filtering and pagination).

```bash
# All pending users
curl "http://localhost:8000/auth/admin/users?status=pending" \
  -H "Authorization: Bearer <admin_token>"

# All users (paginated)
curl "http://localhost:8000/auth/admin/users?skip=0&limit=20" \
  -H "Authorization: Bearer <admin_token>"
```

#### `GET /auth/admin/users/{user_id}`

Get a specific user.

#### `PATCH /auth/admin/users/{user_id}/approve`

Grant access to a user.

```bash
curl -X PATCH http://localhost:8000/auth/admin/users/2/approve \
  -H "Authorization: Bearer <admin_token>"
```

#### `PATCH /auth/admin/users/{user_id}/deny`

Deny a user. A reason is required.

```bash
curl -X PATCH http://localhost:8000/auth/admin/users/2/deny \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Unrecognised email domain."}'
```

#### `PATCH /auth/admin/users/{user_id}/revoke`

Revoke access from a previously approved user.

#### `PATCH /auth/admin/users/{user_id}/role`

Change role (`user` ↔ `super_admin`).

```bash
curl -X PATCH http://localhost:8000/auth/admin/users/2/role \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "super_admin"}'
```

#### `DELETE /auth/admin/users/{user_id}`

Permanently delete a user (not yourself, not another super admin).

#### `GET /auth/admin/stats`

Dashboard summary.

```bash
curl http://localhost:8000/auth/admin/stats \
  -H "Authorization: Bearer <admin_token>"
# → {"total": 10, "by_status": {"pending": 3, "approved": 6, "denied": 1}}
```

---

### Chat (Next.js REST API)

#### `POST /api/chat`

Send a message to the RAG assistant. **Requires approved account.**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What services does Radixweb offer?", "history": []}'
```

Response:

```json
{
  "answer": "Radixweb offers software development services including...",
  "sources": [...]
}
```

#### `POST /api/chat/verify`

Lightweight token + approval check. No body needed.

```bash
curl -X POST http://localhost:8000/api/chat/verify \
  -H "Authorization: Bearer <token>"
```

Returns `200` with user info if approved, `403` if pending/denied/revoked.

---

## Next.js Integration

### Login flow

```typescript
// lib/auth.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    const data = await res.json();
    // Store the token (e.g., httpOnly cookie via a /api/session route)
    return data; // { access_token, token_type, user }
}

export async function chat(token: string, message: string, history: any[]) {
    const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message, history }),
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    return res.json(); // { answer, sources }
}
```

### Middleware (protect chatbot pages)

```typescript
// middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.API_URL || "http://localhost:8000";
const PROTECTED = ["/chat", "/dashboard"];

export async function middleware(req: NextRequest) {
    const path = req.nextUrl.pathname;
    if (!PROTECTED.some((p) => path.startsWith(p))) return NextResponse.next();

    const token = req.cookies.get("access_token")?.value;
    if (!token) return NextResponse.redirect(new URL("/login", req.url));

    const check = await fetch(`${API_BASE}/api/chat/verify`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
    });

    if (!check.ok) return NextResponse.redirect(new URL("/login", req.url));
    return NextResponse.next();
}
```

---

## Gradio Integration

The Gradio UI is protected by the same user database. When `api.py` mounts Gradio with `auth=gradio_auth`, Gradio shows a login form. Users enter their **email** (as username) and **password**. Only `APPROVED` accounts are accepted.

```python
# Already wired in api.py — shown here for reference
from auth_module import gradio_auth

app = gr.mount_gradio_app(
    app,
    gradio_ui,
    path="/",
    auth=gradio_auth,
    auth_message="Enter your approved Radixweb account email and password.",
)
```

---

## Running as a Standalone Service

The auth module can run on a separate port (e.g., 8001) if you want to decouple auth from the main API:

```bash
# From project root
uvicorn auth_module.app:app --host 0.0.0.0 --port 8001 --reload
```

Update `NEXT_PUBLIC_API_URL` in your Next.js `.env.local` to point to the correct host.

---

## Security Notes

| Concern          | Mitigation                                                                                                                              |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| JWT secret       | Change `AUTH_JWT_SECRET` to a random 32+ char string before production                                                                  |
| Token expiry     | Tokens expire after 24 h by default; reduce `AUTH_TOKEN_EXPIRE_MINUTES` for higher security                                             |
| Token revocation | Tokens are DB-verified on every API call; revoking in DB immediately blocks new requests (Gradio sessions survive until the next login) |
| CORS             | `allow_origins=["*"]` in the standalone app — restrict to your frontend domain in production                                            |
| SQLite           | Fine for small to medium deployments; switch `AUTH_DATABASE_URL` to PostgreSQL for production scale                                     |
| Password hashing | bcrypt with default cost factor (12 rounds)                                                                                             |
