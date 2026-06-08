"""
Radixweb Knowledge API
===================================
Endpoints:
  POST /api/scrape/start          – start a full radixweb.com crawl
  GET  /api/scrape/status         – live crawl progress
  GET  /api/scrape/categories     – categories + file counts on disk

  POST /api/ingest                – run pro_implementation ingestion pipeline
  GET  /api/ingest/status         – check whether ingestion is running

  POST /api/pipeline/run          – scrape then ingest in one shot (background)

  GET  /                          – Gradio chat UI (mounted)
"""

import os
import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Security
from fastapi.security import APIKeyHeader
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from pro_implementation.ingest import fetch_documents, create_chunks, create_embeddings
from scraper import run_full_crawl, scrape_state, scrape_lock

KNOWLEDGE_BASE_PATH = Path(__file__).parent / "knowledge-base"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def _require_api_key(key: str = Security(_api_key_header)) -> None:
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected or key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key.")


# ---------------------------------------------------------------------------
# Ingestion helpers
# ---------------------------------------------------------------------------

ingest_lock = threading.Lock()


def _ingestion_body() -> None:
    """Core ingest logic — caller must hold ingest_lock."""
    print("Starting ingestion pipeline...")
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete.")


def _run_ingestion_and_release() -> None:
    """Background task: run ingestion then release the lock acquired by the endpoint."""
    try:
        _ingestion_body()
    except Exception as exc:
        print(f"Ingestion error: {exc}")
    finally:
        ingest_lock.release()


def perform_ingestion() -> bool:
    """Run ingestion with its own lock acquire — used by the scheduler."""
    if not ingest_lock.acquire(blocking=False):
        print("Ingestion already running — skipping.")
        return False
    try:
        _ingestion_body()
        return True
    except Exception as exc:
        print(f"Ingestion error: {exc}")
        return False
    finally:
        ingest_lock.release()


# ---------------------------------------------------------------------------
# Scheduler (hourly auto-ingest)
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        perform_ingestion,
        trigger=CronTrigger(minute=0),
        id="hourly_ingestion",
        name="Hourly Document Ingestion",
        replace_existing=True,
    )
    scheduler.start()
    print("Scheduler started — hourly ingestion configured.")
    yield
    scheduler.shutdown()
    print("Scheduler stopped.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Radixweb Knowledge API",
    description=(
        "Scrape radixweb.com, categorise content into the knowledge-base, "
        "and ingest it via the pro RAG pipeline."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Scraper endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/api/scrape/start",
    summary="Start radixweb.com crawl",
    description=(
        "Launches an async BFS crawl of radixweb.com using Playwright. "
        "Pages are rendered (JS executed), cleaned, converted to Markdown, "
        "and saved under knowledge-base/{category}/. "
        "Returns immediately; poll /api/scrape/status for progress."
    ),
    tags=["Scraper"],
)
async def start_scrape(
    background_tasks: BackgroundTasks,
    max_pages: int = 10000,
    workers: int = 3,
    _: None = Depends(_require_api_key),
):
    if scrape_lock.locked():
        raise HTTPException(status_code=409, detail="Scrape already in progress.")
    background_tasks.add_task(run_full_crawl, max_pages, workers)
    return {
        "message": "Crawl started — ALL sitemap URLs queued, none skipped.",
        "sitemap_urls": "~1961",
        "max_pages": max_pages,
        "workers": workers,
        "status_url": "/api/scrape/status",
    }


@app.get(
    "/api/scrape/status",
    summary="Crawl progress",
    description="Returns the current state of the active (or most recent) crawl.",
    tags=["Scraper"],
)
async def get_scrape_status():
    return scrape_state.to_dict()


@app.get(
    "/api/scrape/categories",
    summary="Knowledge-base category summary",
    description=(
        "Returns every category folder present on disk with a count of "
        ".md files it contains. Reflects the actual filesystem state, not "
        "just the in-memory crawl state."
    ),
    tags=["Scraper"],
)
async def get_categories():
    result: dict[str, dict] = {}

    if not KNOWLEDGE_BASE_PATH.exists():
        return {"categories": result, "total_files": 0}

    total = 0
    for folder in sorted(KNOWLEDGE_BASE_PATH.iterdir()):
        if not folder.is_dir():
            continue
        files = list(folder.rglob("*.md"))
        result[folder.name] = {
            "file_count": len(files),
            "files": [f.name for f in files[:20]],  # preview first 20
        }
        total += len(files)

    return {"categories": result, "total_files": total}


# ---------------------------------------------------------------------------
# Ingest endpoints  (uses pro_implementation)
# ---------------------------------------------------------------------------

@app.post(
    "/api/ingest",
    summary="Trigger manual ingestion",
    description=(
        "Runs the pro_implementation ingestion pipeline in the background: "
        "reads all .md files from knowledge-base/, chunks them with an LLM, "
        "embeds each chunk, and stores them in the Chroma vector database."
    ),
    tags=["Ingestion"],
)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    _: None = Depends(_require_api_key),
):
    if not ingest_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ingestion already running.")
    background_tasks.add_task(_run_ingestion_and_release)
    return {"message": "Ingestion started in background."}


@app.get(
    "/api/ingest/status",
    summary="Check ingestion status",
    description="Returns whether an ingestion pipeline run is currently active.",
    tags=["Ingestion"],
)
async def get_ingest_status():
    return {"is_running": ingest_lock.locked()}


# ---------------------------------------------------------------------------
# Combined pipeline endpoint
# ---------------------------------------------------------------------------

async def _pipeline(max_pages: int, workers: int):
    """Scrape then ingest — runs sequentially inside a background task.
    Caller must have already acquired ingest_lock before scheduling this task."""
    print("=== Pipeline: starting scrape ===")
    await run_full_crawl(max_pages, workers)
    print("=== Pipeline: scrape done, starting ingest ===")
    await asyncio.get_running_loop().run_in_executor(None, _run_ingestion_and_release)
    print("=== Pipeline: ingest done ===")


@app.post(
    "/api/pipeline/run",
    summary="Full scrape → ingest pipeline",
    description=(
        "Runs the complete pipeline: crawl all of radixweb.com "
        "(every URL from sitemap + dynamically discovered links) → "
        "save categorised Markdown → ingest into Chroma. "
        "Sequential in the background."
    ),
    tags=["Pipeline"],
)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    max_pages: int = 10000,
    workers: int = 3,
    _: None = Depends(_require_api_key),
):
    if scrape_lock.locked():
        raise HTTPException(status_code=409, detail="Scrape already in progress.")
    if not ingest_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ingestion already in progress.")
    background_tasks.add_task(_pipeline, max_pages, workers)
    return {
        "message": "Full pipeline started (scrape all URLs → ingest).",
        "max_pages": max_pages,
        "workers": workers,
        "scrape_status_url": "/api/scrape/status",
        "ingest_status_url": "/api/ingest/status",
    }


# ---------------------------------------------------------------------------
# Mount Gradio UI (PRO pipeline)
# ---------------------------------------------------------------------------

import gradio as gr
from pro_implementation.answer import answer_question as _answer_question


def _chat(message: str, history: list) -> str:
    answer, _ = _answer_question(message, history)
    return answer


gradio_ui = gr.ChatInterface(
    fn=_chat,
    title="Radixweb Expert Assistant",
    description="Hybrid RAG · BM25 + Semantic · Local Reranker",
)
app = gr.mount_gradio_app(app, gradio_ui, path="/")
