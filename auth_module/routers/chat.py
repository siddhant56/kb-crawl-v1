"""
auth_module/routers/chat.py
---------------------------
Protected chat endpoints consumed by the Next.js frontend.

Routes
------
POST   /api/chat          – send a message, get RAG answer; auto-saves both turns to DB
GET    /api/chat/history  – load current user's persisted conversation
DELETE /api/chat/history  – clear current user's conversation
POST   /api/chat/verify   – lightweight token + approval check for Next.js middleware
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_module.database import get_db
from auth_module.dependencies import require_approved
from auth_module.models import ChatMessage, ChatSession, GuardrailLog, User
from auth_module.schemas import ChatHistoryResponse, ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["Chat"])

# History window passed to the LLM — older turns are stored in DB but not sent to avoid token overflow
_CONTEXT_LIMIT = 20


def _get_rag_answer(message: str, history: list) -> tuple[str, list]:
    """Lazy-import the RAG pipeline to avoid heavy model loading at startup."""
    from pro_implementation.answer import answer_question  # type: ignore[import]

    result = answer_question(message, history)
    if isinstance(result, tuple):
        answer, sources = result
        return answer, sources if isinstance(sources, list) else []
    return str(result), []


def _get_or_create_session(user_id: int, db: Session) -> ChatSession:
    """Return the user's existing chat session, creating one if absent."""
    session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
    if not session:
        session = ChatSession(user_id=user_id)
        db.add(session)
        db.flush()
    return session


def _classify_input(message: str):
    """Lazy-import wrapper so the guardrails module loads only when the first chat arrives."""
    from pro_implementation.guardrails import classify_input  # type: ignore[import]
    return classify_input(message)


def _log_guardrail(
    db: Session,
    user_id: int,
    rule_id: str,
    message: str,
    *,
    blocked: bool,
) -> None:
    """Write a guardrail audit entry; never raises so a log failure never breaks the chat flow."""
    try:
        db.add(GuardrailLog(
            user_id=user_id,
            direction="input",
            rule_id=rule_id,
            message_snippet=message[:300],
            blocked=blocked,
        ))
        db.commit()
        if blocked:
            print(f"[guardrail] BLOCKED user_id={user_id} rule={rule_id} msg={message[:80]!r}")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("[guardrail] Audit log write failed: %s", exc)


@router.get(
    "/chat/history",
    response_model=ChatHistoryResponse,
    summary="Load saved conversation",
    description="Returns the current user's persisted chat messages in insertion order.",
)
def get_history(
    user: User = Depends(require_approved),
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    session = db.query(ChatSession).filter(ChatSession.user_id == user.id).first()
    if not session:
        return ChatHistoryResponse(messages=[])
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.turn_index)
        .all()
    )
    return ChatHistoryResponse(messages=messages)


@router.delete(
    "/chat/history",
    status_code=204,
    summary="Clear saved conversation",
    description="Deletes all messages and the session for the current user.",
)
def clear_history(
    user: User = Depends(require_approved),
    db: Session = Depends(get_db),
) -> None:
    session = db.query(ChatSession).filter(ChatSession.user_id == user.id).first()
    if session:
        db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
        db.delete(session)
        db.commit()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with the RAG assistant",
    description=(
        "Send a question to the Radixweb Knowledge Base RAG assistant. "
        "Requires an APPROVED account JWT. The full history is stored in the DB; "
        "only the most recent 20 turns are sent to the LLM to avoid token overflow."
    ),
)
def chat(
    body: ChatRequest,
    user: User = Depends(require_approved),
    db: Session = Depends(get_db),
) -> ChatResponse:
    # ── Input guardrail ──────────────────────────────────────────────────────
    violation = _classify_input(body.message)
    _log_guardrail(db, user.id, violation.rule_id if violation else "allowed", body.message, blocked=violation is not None)
    if violation:
        return ChatResponse(answer=violation.response, sources=[])

    # Compact: only send the last N turns as LLM context
    trimmed = body.history[-_CONTEXT_LIMIT:] if len(body.history) > _CONTEXT_LIMIT else body.history

    try:
        answer, sources = _get_rag_answer(body.message, trimmed)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="RAG backend is not available. Ensure pro_implementation is installed.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}")

    # Persist both turns
    session = _get_or_create_session(user.id, db)
    next_index = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
    db.add(ChatMessage(session_id=session.id, role="user", content=body.message, turn_index=next_index))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=answer, turn_index=next_index + 1))
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(answer=answer, sources=sources)


@router.post(
    "/chat/verify",
    summary="Verify chat access",
    description=(
        "Returns the caller's identity if their token is valid and their account is approved. "
        "Used by Next.js middleware to guard chatbot pages without a DB roundtrip on the frontend."
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
