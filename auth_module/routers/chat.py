"""
auth_module/routers/chat.py
---------------------------
Protected chat endpoints consumed by the Next.js frontend.

Routes
------
POST /api/chat          – send a message to the RAG assistant (APPROVED users only)
POST /api/chat/verify   – lightweight token + approval check for Next.js middleware
"""

from fastapi import APIRouter, Depends, HTTPException

from auth_module.dependencies import require_approved
from auth_module.models import User
from auth_module.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["Chat"])


def _get_rag_answer(message: str, history: list) -> tuple[str, list]:
    """Lazy-import the RAG answer function to avoid heavy loading at module init."""
    from pro_implementation.answer import answer_question  # type: ignore[import]

    result = answer_question(message, history)
    if isinstance(result, tuple):
        answer, sources = result
        return answer, sources if isinstance(sources, list) else []
    return str(result), []


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with the RAG assistant",
    description=(
        "Send a question to the Radixweb Knowledge Base RAG assistant. "
        "**Requires a valid JWT Bearer token from an APPROVED account.** "
        "Designed to be called from the Next.js frontend.\n\n"
        "Include prior turns in `history` to maintain conversation context."
    ),
)
def chat(
    body: ChatRequest,
    _user: User = Depends(require_approved),
) -> ChatResponse:
    try:
        answer, sources = _get_rag_answer(body.message, body.history)
        return ChatResponse(answer=answer, sources=sources)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="RAG backend is not available. Ensure pro_implementation is installed.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}")


@router.post(
    "/chat/verify",
    summary="Verify chat access",
    description=(
        "Returns the caller's identity if their token is valid **and** their account "
        "is `approved`. Use this in Next.js middleware (`middleware.ts`) to protect "
        "chatbot pages without a full database roundtrip on the frontend.\n\n"
        "Returns `403` if the account exists but is not yet approved."
    ),
)
def verify_chat_access(user: User = Depends(require_approved)) -> dict:
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
    }
