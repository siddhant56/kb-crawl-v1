# Company Knowledge Base — RAG System

A production-grade **Retrieval-Augmented Generation (RAG)** system that crawls the entire company website, builds a structured knowledge base from it, and exposes a Gradio chat UI + REST API for asking questions about the company.

---

## How It Works

```
company.com  ──►  Playwright crawler  ──►  knowledge-base/*.md
                                                    │
                                                    ▼
                                         LLM chunking + embeddings
                                                    │
                                                    ▼
                                            ChromaDB vector store
                                                    │
                                                    ▼
                                         Gradio Chat UI  /  REST API
```

1. **Scrape** — A headless Chromium browser crawls all ~1,961 pages of the company website, strips boilerplate, and saves each page as a Markdown file under `knowledge-base/{category}/`.
2. **Ingest** — An LLM (GPT-4.1-nano) reads each Markdown file and generates structured chunks (headline + summary + original text), which are embedded and stored in ChromaDB.
3. **Answer** — Users chat via the Gradio UI or call the API; the system retrieves the most relevant chunks (with query rewriting + LLM re-ranking) and generates an answer.

---

## Environment Variables

Create a `.env` file in the project root. All variables are loaded automatically at startup via `python-dotenv`.

```env
# ── Required ───────────────────────────────────────────────────────────────

# OpenAI API key — used for embeddings (text-embedding-3-large) in both
# pipelines, and for GPT-4.1-nano in the basic pipeline (implementation/)
# and the pro ingestion chunking (pro_implementation/ingest.py).
OPENAI_API_KEY=sk-...

# ── Required for Pro Pipeline answers ──────────────────────────────────────

# The pro answer pipeline (pro_implementation/answer.py) uses LiteLLM,
# which routes to different providers based on the model string prefix.
# The default model is "groq/openai/gpt-oss-120b" — set the matching key.

# If using Groq:
GROQ_API_KEY=gsk_...

# If you switch MODEL in pro_implementation/answer.py to an OpenAI model
# (e.g. "openai/gpt-4.1"), OPENAI_API_KEY above covers it — no extra key needed.

# If you switch to Anthropic (e.g. "anthropic/claude-3-5-sonnet"):
# ANTHROPIC_API_KEY=sk-ant-...

# ── Optional ───────────────────────────────────────────────────────────────

# LiteLLM verbose logging — set to True to debug LLM calls
# LITELLM_LOG=DEBUG
```

### Which key is needed for what

| Feature | Key Required |
|---|---|
| Embeddings (both pipelines) | `OPENAI_API_KEY` |
| Basic pipeline answers (`implementation/`) | `OPENAI_API_KEY` |
| Pro ingestion chunking (`pro_implementation/ingest.py`) | `OPENAI_API_KEY` |
| Pro pipeline answers (`pro_implementation/answer.py`) | Depends on model prefix in `MODEL` variable — default needs `GROQ_API_KEY` |
| Web scraping | None — Playwright uses a local browser |

---

## Prerequisites

- Python 3.11 or higher
- A `.env` file with at minimum `OPENAI_API_KEY`

---

## Installation

**1. Clone the repository**
```bash
git clone <repo-url>
cd <project-folder>
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**4. Install the Playwright browser**

This is a separate step — Playwright downloads a local Chromium binary.
```bash
playwright install chromium
```

**5. Create your `.env` file**
```bash
cp .env.example .env   # if the example exists, otherwise create it manually
# then fill in your API keys
```

---

## Running the Project

### Option A — Full API + Chat UI (recommended)

Starts the FastAPI server with the Gradio chat UI mounted at `/`.

```bash
uvicorn api:app --reload --port 8000
```

| URL | Description |
|---|---|
| `http://localhost:8000` | Gradio chat UI |
| `http://localhost:8000/docs` | Swagger interactive API docs |
| `http://localhost:8000/redoc` | ReDoc API docs |

The server also starts an **hourly background scheduler** that automatically re-ingests the knowledge base at the top of every hour.

---

### Option B — Run the crawler standalone

Scrapes all ~1,961 pages of the company website and saves Markdown files to `knowledge-base/`. Does not require the API server to be running.

```bash
python run_crawl.py
```

---

### Option C — Run basic ingestion standalone

Uses the **basic pipeline** (LangChain + fixed-size text splitting). Reads `knowledge-base/`, chunks and embeds all documents, stores vectors in `vector_db/`.

```bash
python implementation/ingest.py
```

---

### Option D — Run pro ingestion standalone

Uses the **pro pipeline** (LLM-assisted chunking). Each document is sent to GPT-4.1-nano, which generates structured chunks (headline + summary + original text). Stores vectors in `preprocessed_db/`.

```bash
python pro_implementation/ingest.py
```

> This is slower and uses more API credits than the basic pipeline, but produces significantly better retrieval quality.

---

## API Endpoints

### Scraper

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scrape/start` | Start a full crawl of the company website (runs in background) |
| `GET` | `/api/scrape/status` | Live crawl progress (pages scraped, current URL, categories) |
| `GET` | `/api/scrape/categories` | File count per category folder on disk |

**Start a crawl:**
```bash
curl -X POST "http://localhost:8000/api/scrape/start"

# With custom options:
curl -X POST "http://localhost:8000/api/scrape/start?max_pages=500&workers=5"
```

**Check crawl progress:**
```bash
curl http://localhost:8000/api/scrape/status
```

**See what's been saved to disk:**
```bash
curl http://localhost:8000/api/scrape/categories
```

### Ingestion

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ingest` | Trigger pro-pipeline ingestion (runs in background) |
| `GET` | `/api/ingest/status` | Check whether ingestion is currently running |

**Trigger ingestion:**
```bash
curl -X POST http://localhost:8000/api/ingest
```

**Check ingestion status:**
```bash
curl http://localhost:8000/api/ingest/status
```

### Full Pipeline

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/pipeline/run` | Scrape then ingest sequentially in one background task |

**Run everything in one shot:**
```bash
curl -X POST "http://localhost:8000/api/pipeline/run"
```

---

## Typical First-Run Workflow

```bash
# 1. Start the server
uvicorn api:app --reload --port 8000

# 2. Kick off the full pipeline (scrape + ingest)
curl -X POST "http://localhost:8000/api/pipeline/run"

# 3. Monitor scrape progress (poll until status = "completed")
curl http://localhost:8000/api/scrape/status

# 4. Monitor ingest progress
curl http://localhost:8000/api/ingest/status

# 5. Open the chat UI once ingestion is done
open http://localhost:8000
```

> The scrape takes roughly **30–60 minutes** for ~1,961 pages with 3 workers. Ingestion takes **20–60 minutes** depending on document count and LLM throughput.

---

## Project Structure

```
project-root/
│
├── api.py                      # FastAPI app — all endpoints + hourly scheduler
├── app.py                      # Gradio chat UI
├── run_crawl.py                # Standalone crawler entry point
│
├── scraper/                    # Web scraping module
│   ├── sitemap.py              # Parse the company website sitemap
│   ├── crawler.py              # Async concurrent Playwright crawler
│   ├── extractor.py            # Strip boilerplate, extract main content
│   ├── converter.py            # HTML → Markdown
│   ├── categorizer.py          # URL → category + filename
│   └── state.py                # Shared crawl state + threading lock
│
├── implementation/             # Basic RAG pipeline (LangChain)
│   ├── ingest.py               # Fixed-size chunking → ChromaDB (vector_db/)
│   └── answer.py               # Single retrieval → LLM answer
│
├── pro_implementation/         # Advanced RAG pipeline
│   ├── ingest.py               # LLM chunking → ChromaDB (preprocessed_db/)
│   └── answer.py               # Query rewrite + dual retrieval + rerank → answer
│
├── knowledge-base/             # Crawler output — one subfolder per category
│   ├── about/
│   ├── blog/
│   ├── company/
│   ├── hire-developers/
│   ├── industries/
│   ├── resources/
│   ├── services/
│   └── case-studies/
│
├── vector_db/                  # ChromaDB store — basic pipeline
├── preprocessed_db/            # ChromaDB store — pro pipeline
│
├── docs/                       # Detailed documentation
│   ├── overview.md             # Architecture + how to run
│   ├── scraper.md              # Scraper module deep dive
│   ├── rag-pipelines.md        # Both RAG pipelines explained
│   ├── api-reference.md        # All API endpoints with examples
│   └── key-functions.md        # Important functions reference
│
├── requirements.txt
└── pyproject.toml
```

---

## Documentation

Detailed documentation lives in the `docs/` folder:

- **[docs/overview.md](docs/overview.md)** — Architecture diagram, folder structure, pipeline comparison
- **[docs/scraper.md](docs/scraper.md)** — How the crawler, extractor, and categoriser work
- **[docs/rag-pipelines.md](docs/rag-pipelines.md)** — Basic vs. pro pipeline explained function by function
- **[docs/api-reference.md](docs/api-reference.md)** — Every API endpoint with request/response examples
- **[docs/key-functions.md](docs/key-functions.md)** — Quick reference for all important functions

---

## Two RAG Pipelines at a Glance

| | Basic (`implementation/`) | Pro (`pro_implementation/`) |
|---|---|---|
| Chunking | Fixed 500-char splits | LLM generates headline + summary + text |
| Retrieval | Single query, top 10 | Dual query (original + rewritten), top 20 each, merged, re-ranked to top 10 |
| Generation | LangChain ChatOpenAI | LiteLLM (model-agnostic) |
| Vector store | `vector_db/` | `preprocessed_db/` |
| Used by | Gradio chat UI | API ingestion + pro answering |
