# Document Upload Feature — Guide

This guide covers everything about the document upload feature: what it does, how permissions work, how sensitive data is handled, and how to test it end-to-end.

---

## Table of Contents

1. [Overview](#1-overview)
2. [How upload access works](#2-how-upload-access-works)
3. [Supported file types](#3-supported-file-types)
4. [Sensitive data sanitization](#4-sensitive-data-sanitization)
5. [Document processing pipeline](#5-document-processing-pipeline)
6. [Admin: granting and revoking upload access](#6-admin-granting-and-revoking-upload-access)
7. [Using the upload UI](#7-using-the-upload-ui)
8. [API reference (curl)](#8-api-reference-curl)
9. [SQLite migration (new environments)](#9-sqlite-migration-new-environments)
10. [Common errors and fixes](#10-common-errors-and-fixes)

---

## 1. Overview

Approved users can be granted **document upload access** by a super admin. Once granted, they can upload PDF, DOCX, TXT, or Markdown files through the `/upload` page. Each uploaded document is:

- Converted to Markdown
- Scanned and sanitized for sensitive data (API keys, PII, pricing, credentials)
- Chunked, embedded with `text-embedding-3-small`, and appended to the ChromaDB knowledge base
- Immediately queryable through the chat interface

Documents are stored in `knowledge-base/{category}/` and indexed incrementally — no full rebuild is needed.

---

## 2. How upload access works

Upload access is a separate permission from chat access. The relationship is:

```
registered → pending → approved (chat access)
                           └→ upload_access = true  (upload + chat)
```

A user must be **approved** before upload access can be granted. Upload access can be revoked independently without revoking chat access.

The `upload_access` flag is stored in the `users` table (`upload_access BOOLEAN NOT NULL DEFAULT 0`) and also embedded in the JWT so the Next.js middleware can gate the `/upload` page without a network call.

---

## 3. Supported file types

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text extracted page-by-page. Image-only PDFs will fail (< 50 chars). |
| Word | `.docx` | Heading styles (Heading 1–4) are converted to `#`/`##`/`###`/`####` markdown. |
| Plain text | `.txt` | Wrapped in a standard markdown template with the document title. |
| Markdown | `.md` | Used as-is (already structured). |

**Limits:** Maximum 50 MB per file. Files with fewer than 50 characters of extracted text are rejected.

---

## 4. Sensitive data sanitization

Every document passes through `auth_module/sanitizer.py` before being embedded. The following patterns are detected and replaced with `[REDACTED:<CATEGORY>]`:

### API Keys & Tokens

| Pattern | Example |
|---------|---------|
| OpenAI secret keys | `sk-proj-abc123...` |
| AWS access key IDs | `AKIA1234567890ABCD` |
| AWS secret keys | `aws_secret_key=abc...` |
| Google API keys | `AIzaSy...` |
| GitHub tokens | `ghp_abc123...` |
| Stripe keys | `sk_live_abc123...` |
| SendGrid keys | `SG.abc...` |
| Twilio Account SIDs | `ACabc123...` |
| Bearer tokens in docs | `Authorization: Bearer eyJ...` |
| JWT tokens | `eyJhbGciOiJIUzI1NiJ9.eyJ...` |

### Credentials & Secrets

| Pattern | Example |
|---------|---------|
| Key=value secrets | `api_key=mysecret`, `secret_key: abc123` |
| Passwords | `password=abc`, `passwd: xyz` |
| Connection strings | `postgresql://user:pass@host/db` |
| PEM private keys | `-----BEGIN RSA PRIVATE KEY-----` |
| Generic 32–64 char hex strings | `a3f8d2c1e5b7a9f0c2d4e6b8...` |

### Pricing & Financial Data

| Pattern | Example |
|---------|---------|
| Currency amounts | `$299/month`, `€500`, `USD 1,000` |
| Labeled pricing lines | `Price: $99/user/month` |
| Promo/discount codes | `promo_code=SAVE20` |

### PII (Personal Identifiable Information)

| Pattern | Example |
|---------|---------|
| Email addresses | `john.doe@example.com` |
| Phone numbers | `+1-800-555-1234`, `(415) 555-0100` |
| US Social Security Numbers | `123-45-6789` |
| Credit card numbers | `4111 1111 1111 1111` |

### Client / Customer Data

| Pattern | Example |
|---------|---------|
| Labeled client lines | `Client: Acme Corp`, `Customer Name: John Smith` |
| Contract/invoice numbers | `Invoice: INV-2024-001`, `Contract #: CTR-2024-ABC` |

### Redaction behavior

- Each match is replaced inline: `sk-proj-abc123` → `[REDACTED:API_KEY]`
- The surrounding context is preserved — only the secret value is removed
- The upload response includes a full redaction summary by category
- Documents with redactions are still indexed (not rejected)

To test the sanitizer directly:

```python
from auth_module.sanitizer import sanitize

text = "Our API key is sk-proj-abc123 and pricing is $99/month."
clean, report = sanitize(text)
print(clean)
# Our API key is [REDACTED:API_KEY] and pricing is [REDACTED:PRICING].
print(report)
# Redacted 2 items:
#   API_KEY: 1
#   PRICING: 1
```

---

## 5. Document processing pipeline

```
Upload (multipart/form-data)
    │
    ├── Validate: extension, MIME type, size (≤ 50 MB)
    │
    ├── Extract text:
    │     PDF   → pypdf page-by-page extraction
    │     DOCX  → python-docx with heading style → markdown header mapping
    │     TXT   → decode UTF-8
    │     MD    → pass-through
    │
    ├── Wrap in standard markdown template (# Title \n\n---\n\n{body})
    │
    ├── Sanitize (auth_module/sanitizer.py)
    │     → Replace all sensitive patterns with [REDACTED:CATEGORY]
    │
    ├── Write to: knowledge-base/{category}/{slug}.md
    │
    ├── Chunk (MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter)
    │     chunk_size=600, chunk_overlap=150, min_length=40
    │     breadcrumb prepended to each chunk
    │
    ├── Embed (text-embedding-3-small, batches of 500)
    │
    ├── Append to ChromaDB (upsert with stable hash-based IDs)
    │     → Removes old chunks for this source first (overwrite semantics)
    │
    └── Rebuild TF-IDF BM25 index (incremental — replaces entries for this source)
```

The operation is **synchronous** — the HTTP response is returned after all steps complete. Expect 10–30 seconds for a typical document.

---

## 6. Admin: granting and revoking upload access

### Via the admin panel (UI)

1. Log in as super admin → `/admin`
2. Find the approved user in the table
3. Click **Grant Upload** (green outlined button) to enable upload access
4. An **Upload** badge appears in the user's role column
5. To remove: click **Revoke Upload** (orange outlined button)

### Via curl

```bash
# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Grant upload access to user ID 2
curl -X PATCH http://localhost:8000/auth/admin/users/2/grant-upload \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Revoke upload access from user ID 2
curl -X PATCH http://localhost:8000/auth/admin/users/2/revoke-upload \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Expected response:

```json
{
  "id": 2,
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "user",
  "status": "approved",
  "upload_access": true,
  "created_at": "2024-01-15T10:00:00"
}
```

**Note:** The user must log out and log back in for the `upload_access` flag in their JWT to update. The backend always re-reads from the database, so the API-level guard (`require_upload_access`) is effective immediately.

---

## 7. Using the upload UI

1. Log in with an account that has `upload_access = true`
2. Click **Upload Docs** in the top navigation bar
3. Drag & drop a file onto the drop zone, or click to browse
4. Select a **category** from the dropdown (see category list below)
5. Optionally provide a **title** (defaults to the filename stem)
6. Click **Upload to knowledge base**
7. Wait 10–30 seconds for processing
8. Review the result:
   - Chunks indexed and replaced counts
   - Sanitization report (which categories of sensitive data were found and redacted)

### Categories

| Category | Use for |
|----------|---------|
| `blog` | Blog posts, company news, insights |
| `services` | Service descriptions, solution pages |
| `hire-developers` | Developer hiring, team profiles |
| `case-studies` | Client case studies, success stories |
| `industries` | Industry-specific content |
| `resources` | Guides, whitepapers, reports |
| `about` | About pages, leadership, company culture |
| `company` | Contact, careers, company policies |
| `uploads` | General catch-all for user uploads |

---

## 8. API reference (curl)

### List categories

```bash
curl http://localhost:8000/api/upload/categories
```

Response:
```json
{"categories": ["blog", "services", "hire-developers", ...]}
```

### Upload a document

```bash
USER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"UserPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $USER_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "category=services" \
  -F "title=Q4 Services Overview"
```

Expected response:
```json
{
  "filename": "document.pdf",
  "saved_as": "document.md",
  "category": "services",
  "chunks_added": 18,
  "chunks_replaced": 0,
  "sanitization": {
    "redactions_total": 2,
    "by_category": {
      "PII_EMAIL": 1,
      "PRICING": 1
    }
  },
  "uploaded_by": "user@example.com"
}
```

### Re-upload (overwrite)

Upload the same filename again — existing chunks are automatically removed and replaced:

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $USER_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "category=services"
```

The response will show `chunks_replaced > 0`.

---

## 9. SQLite migration (new environments)

The `upload_access` column must be added to the `users` table in any environment where the `auth.db` was created before this feature was added.

Run this **once** from the project root:

```bash
uv run python -c "
import sqlite3
conn = sqlite3.connect('auth.db')
cols = [row[1] for row in conn.execute('PRAGMA table_info(users)').fetchall()]
if 'upload_access' not in cols:
    conn.execute('ALTER TABLE users ADD COLUMN upload_access BOOLEAN NOT NULL DEFAULT 0')
    conn.commit()
    print('Migration applied.')
else:
    print('Column already exists — no migration needed.')
conn.close()
"
```

For brand-new environments, the column is added automatically by SQLAlchemy's `create_tables()` on first startup.

---

## 10. Common errors and fixes

### `403 Upload access not granted`

The user is approved but does not have `upload_access = true`.

**Fix:** A super admin must go to `/admin` and click **Grant Upload** for that user.

### `415 Unsupported file type`

The file extension is not one of `.pdf`, `.docx`, `.txt`, `.md`.

**Fix:** Convert the file to a supported format before uploading.

### `413 File exceeds the 50 MB limit`

**Fix:** Split the document into smaller parts or compress it.

### `422 Extracted text is too short`

The file was parsed successfully but produced fewer than 50 characters of text. Common causes:
- PDF is image-only (scanned without OCR)
- DOCX contains only images or tables
- File is actually empty

**Fix:** Ensure the document contains selectable/searchable text. For scanned PDFs, run OCR first (e.g. with Tesseract).

### `500 Embedding failed`

Usually means the OpenAI API is unreachable or the API key is invalid.

**Fix:** Check `OPENAI_API_KEY` in `.env` and verify the key is active at platform.openai.com.

### Upload access not reflected in nav after admin grants it

The JWT is issued at login time and cached for 24 hours. The backend enforces the permission from the database immediately, but the frontend nav reads `upload_access` from the token.

**Fix:** The user must log out and log in again after upload access is granted to refresh their token.

---

## Quick reference

| Item | Value |
|------|-------|
| Upload endpoint | `POST /api/upload` |
| Categories endpoint | `GET /api/upload/categories` |
| Grant upload | `PATCH /auth/admin/users/{id}/grant-upload` |
| Revoke upload | `PATCH /auth/admin/users/{id}/revoke-upload` |
| Max file size | 50 MB |
| Supported formats | PDF, DOCX, TXT, MD |
| Storage location | `knowledge-base/{category}/{slug}.md` |
| Embedding model | `text-embedding-3-small` |
| Chunk size | 600 chars / 150 overlap |
