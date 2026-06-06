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

from fastapi import FastAPI, HTTPException, BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from pro_implementation.ingest import fetch_documents, create_chunks, create_embeddings
from scraper import run_full_crawl, scrape_state, scrape_lock

KNOWLEDGE_BASE_PATH = Path(__file__).parent / "knowledge-base"

# ---------------------------------------------------------------------------
# Ingestion helpers
# ---------------------------------------------------------------------------

ingest_lock = threading.Lock()


def perform_ingestion() -> bool:
    """Run the full pro_implementation ingest pipeline. Thread-safe."""
    if not ingest_lock.acquire(blocking=False):
        print("Ingestion already running — skipping.")
        return False
    try:
        print("Starting ingestion pipeline...")
        documents = fetch_documents()
        chunks = create_chunks(documents)
        create_embeddings(chunks)
        print("Ingestion complete.")
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
async def trigger_ingestion(background_tasks: BackgroundTasks):
    if ingest_lock.locked():
        raise HTTPException(status_code=409, detail="Ingestion already running.")
    background_tasks.add_task(perform_ingestion)
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
    """Scrape then ingest — runs sequentially inside a background task."""
    print("=== Pipeline: starting scrape ===")
    await run_full_crawl(max_pages, workers)
    print("=== Pipeline: scrape done, starting ingest ===")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, perform_ingestion)
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
):
    if scrape_lock.locked():
        raise HTTPException(status_code=409, detail="Scrape already in progress.")
    if ingest_lock.locked():
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
# Mount Gradio UI
# ---------------------------------------------------------------------------

import gradio as gr
from app import build_app

gradio_ui = build_app()
app = gr.mount_gradio_app(app, gradio_ui, path="/")
