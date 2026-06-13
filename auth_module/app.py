"""
auth_module/app.py
------------------
Standalone FastAPI application for the RBAC auth service.

Run independently:
    uvicorn auth_module.app:app --host 0.0.0.0 --port 8001 --reload

Or import the routers/helpers and mount them on the main app (see api.py).

Swagger UI: http://localhost:8001/docs
ReDoc:       http://localhost:8001/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth_module.database import create_tables
from auth_module.routers.admin import router as admin_router
from auth_module.routers.auth import router as auth_router
from auth_module.routers.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


def create_app(cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(
        title="Radixweb RBAC Auth Service",
        description=(
            "## Role-Based Access Control for the Radixweb RAG System\n\n"
            "### Roles\n"
            "| Role | Can do |\n"
            "|------|--------|\n"
            "| `user` | Access Gradio UI + chatbot after approval |\n"
            "| `super_admin` | Everything above + manage all user accounts |\n\n"
            "### User lifecycle\n"
            "1. User calls `POST /auth/register` → status = **pending**\n"
            "2. Super admin calls `PATCH /auth/admin/users/{id}/approve` → status = **approved**\n"
            "3. User calls `POST /auth/login` → receives JWT Bearer token\n"
            "4. Token is sent in `Authorization: Bearer <token>` header to access protected routes\n\n"
            "### First-time setup\n"
            "Call `POST /auth/admin/init` once to create the first super admin. "
            "That endpoint is automatically disabled afterwards."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(chat_router)

    return app


app = create_app()
