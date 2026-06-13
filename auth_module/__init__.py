"""
auth_module
-----------
Role-Based Access Control for the Radixweb RAG system.

Quick integration with the main FastAPI app:

    from auth_module import auth_router, admin_router, chat_router, create_tables, gradio_auth

    # 1. Create tables on startup
    create_tables()

    # 2. Mount all RBAC routes
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(chat_router)

    # 3. Protect Gradio with the RBAC auth function
    app = gr.mount_gradio_app(app, gradio_ui, path="/", auth=gradio_auth,
                              auth_message="Login with your approved Radixweb account.")
"""

from auth_module.database import create_tables
from auth_module.gradio_auth import gradio_auth
from auth_module.routers.admin import router as admin_router
from auth_module.routers.auth import router as auth_router
from auth_module.routers.chat import router as chat_router
from auth_module.routers.upload import router as upload_router

__all__ = [
    "auth_router",
    "admin_router",
    "chat_router",
    "upload_router",
    "create_tables",
    "gradio_auth",
]
