# Project Overview & Architecture

## What This Project Does

This project is a **production RAG (Retrieval-Augmented Generation) system** for the company. It has three main jobs:

1. **Crawl** — Scrapes the entire company website (~1,961 URLs) using a headless browser and saves every page as a Markdown file, organised into category folders inside `knowledge-base/`.
2. **Ingest** — Reads those Markdown files, chunks them (either naively or via LLM), embeds each chunk, and stores the vectors in a ChromaDB database.
3. **Answer** — A Gradio chat UI lets users ask questions; the system retrieves relevant chunks from ChromaDB and generates an answer using an LLM.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI  (api.py)                         │
│                                                                  │
│   POST /api/scrape/start   ──►  scraper/  module                │
│   POST /api/ingest         ──►  pro_implementation/ingest.py    │
│   POST /api/pipeline/run   ──►  scrape then ingest, sequential  │
│   GET  /                   ──►  Gradio UI (app.py)              │
└─────────────────────────────────────────────────────────────────┘
         │                                │
         ▼                                ▼
┌─────────────────┐             ┌──────────────────────┐
│   scraper/      │             │  pro_implementation/ │
│                 │             │                      │
│  sitemap.py     │             │  ingest.py           │
│  crawler.py     │  writes     │   └─ LLM chunking    │
│  extractor.py   │──────────►  │   └─ OpenAI embeds   │
│  converter.py   │  .md files  │   └─ ChromaDB store  │
│  categorizer.py │             │                      │
│  state.py       │             │  answer.py           │
└─────────────────┘             │   └─ query rewrite   │
        │                       │   └─ dual retrieval  │
        ▼                       │   └─ LLM re-rank     │
┌─────────────────┐             └──────────────────────┘
│  knowledge-base/│                       │
│  ├─ about/      │                       ▼
│  ├─ blog/       │             ┌──────────────────────┐
│  ├─ company/    │             │  preprocessed_db/    │
│  ├─ services/   │             │  (ChromaDB vectors)  │
│  ├─ ...         │             └──────────────────────┘
└─────────────────┘                       │
                                          ▼
                               ┌──────────────────────┐
                               │   Gradio Chat UI     │
                               │   (app.py / api.py)  │
                               └──────────────────────┘
```

---

## Folder Structure

```
project-root/
│
├── api.py                      # FastAPI app — all HTTP endpoints + scheduler
├── app.py                      # Gradio chat UI definition
├── run_crawl.py                # Standalone script to run the crawler directly
│
├── scraper/                    # Web scraping module
│   ├── __init__.py             # Public exports
│   ├── sitemap.py              # Fetch all URLs from sitemap.xml
│   ├── crawler.py              # Async concurrent Playwright crawler
│   ├── extractor.py            # Strip boilerplate HTML, extract main content
│   ├── converter.py            # Convert cleaned HTML → Markdown
│   ├── categorizer.py          # URL → category folder + filename
│   └── state.py                # Shared crawl state + threading lock
│
├── implementation/             # Basic RAG pipeline (LangChain-based)
│   ├── ingest.py               # Load .md files, split, embed, store in ChromaDB
│   └── answer.py               # Retrieve + generate answer (LangChain)
│
├── pro_implementation/         # Advanced RAG pipeline (OpenAI SDK + LiteLLM)
│   ├── ingest.py               # LLM-assisted chunking + OpenAI embeddings
│   └── answer.py               # Query rewrite + dual retrieval + LLM re-rank
│
├── knowledge-base/             # Output of the crawler — one folder per category
│   ├── about/
│   ├── blog/
│   ├── company/
│   ├── services/
│   └── ...
│
├── vector_db/                  # ChromaDB store for basic implementation
├── preprocessed_db/            # ChromaDB store for pro implementation
│
├── docs/                       # This documentation
├── requirements.txt
└── pyproject.toml
```

---

## Two RAG Pipelines

The project ships two versions of the RAG pipeline:

| | Basic (`implementation/`) | Pro (`pro_implementation/`) |
|---|---|---|
| **Chunking** | Fixed-size `RecursiveCharacterTextSplitter` (500 chars, 200 overlap) | LLM generates headline + summary + original text per chunk |
| **Embeddings** | OpenAI `text-embedding-3-large` via LangChain | OpenAI `text-embedding-3-large` via OpenAI SDK directly |
| **Storage** | ChromaDB at `vector_db/` | ChromaDB at `preprocessed_db/` |
| **Retrieval** | Single vector query | Dual query (original + rewritten), merged, then LLM re-ranked |
| **Generation** | LangChain `ChatOpenAI` | LiteLLM `completion()` (model-agnostic) |
| **Used by API** | `app.py` chat UI (default) | `api.py` ingestion + advanced chat |

The **Gradio UI** (`app.py`) calls `implementation/answer.py` by default. The **API ingestion** (`POST /api/ingest`) calls `pro_implementation/ingest.py`.

---

## Environment Variables

Create a `.env` file in the project root with:

```
OPENAI_API_KEY=sk-...
```

All Python files call `load_dotenv(override=True)` at startup, so the `.env` file is loaded automatically. The `override=True` flag means the `.env` file always wins over any shell-level variable of the same name.

---

## Scheduler

`api.py` starts an **APScheduler** `BackgroundScheduler` on app startup that calls `perform_ingestion()` once per hour (at minute 0 of every hour). This keeps the vector database fresh as the knowledge base grows. The scheduler shuts down cleanly when the FastAPI app stops via the `lifespan` context manager.

---

## How to Run

**Start the full API + UI:**
```bash
uvicorn api:app --reload --port 8000
```
Visit `http://localhost:8000` for the Gradio chat UI, or `http://localhost:8000/docs` for the interactive API docs.

**Run the crawler standalone:**
```bash
python run_crawl.py
```

**Run basic ingestion standalone:**
```bash
python implementation/ingest.py
```

**Run pro ingestion standalone:**
```bash
python pro_implementation/ingest.py
```

> **First-time setup:** After `pip install -r requirements.txt`, run `playwright install chromium` to download the browser binary.
