import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from implementation.ingest import fetch_documents, create_chunks, create_embeddings


# Create a lock to prevent concurrent ingestions
ingest_lock = threading.Lock()

def perform_ingestion():
    """
    Core function to perform the document ingestion pipeline.
    It fetches documents, creates chunks, and generates embeddings.
    Thread-safe to prevent multiple ingestions running concurrently.
    """
    if not ingest_lock.acquire(blocking=False):
        print("Ingestion is already in progress. Skipping this run.")
        return False
    
    try:
        print("Starting scheduled knowledge-base ingestion...")
        documents = fetch_documents()
        chunks = create_chunks(documents)
        vectorstore = create_embeddings(chunks)
        print("Ingestion complete!")
        return True
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return False
    finally:
        ingest_lock.release()

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
    print("Background scheduler started. Hourly ingestion job configured.")
    yield
    scheduler.shutdown()
    print("Background scheduler shutdown.")

app = FastAPI(
    title="InsureLLM Ingestion API",
    description="API to manage autonomous document ingestion and processing for knowledge bases.",
    version="1.0.0",
    lifespan=lifespan
)

@app.post(
    "/api/ingest",
    summary="Trigger Manual Ingestion",
    description="Manually triggers the document ingestion pipeline. The process runs in the background. It fetches documents from the knowledge-base, chunks them, and updates the vector database.",
    response_description="Confirmation that the ingestion task has started.",
    tags=["Ingestion"]
)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Endpoint to manually trigger the document ingestion pipeline.
    Useful for immediately updating the vector database after adding new documents.
    """
    if ingest_lock.locked():
        raise HTTPException(status_code=409, detail="Ingestion is already running.")
    
    background_tasks.add_task(perform_ingestion)
    return {"message": "Ingestion task triggered and running in the background."}

@app.get(
    "/api/ingest/status",
    summary="Check Ingestion Status",
    description="Returns whether an ingestion process is currently running.",
    tags=["Ingestion"]
)
async def check_ingest_status():
    """
    Endpoint to check the status of the ingestion pipeline.
    Returns:
        is_running: Boolean indicating if ingestion is active.
    """
    return {"is_running": ingest_lock.locked()}

# Mount the Gradio App
import gradio as gr
from app import build_app

gradio_ui = build_app()
app = gr.mount_gradio_app(app, gradio_ui, path="/")


