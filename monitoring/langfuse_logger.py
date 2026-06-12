"""
Langfuse self-hosted integration — single observability platform for this project.
Provides a LangChain CallbackHandler + helper for session scoring.

Targets Langfuse v4.x (langfuse.langchain.CallbackHandler).
LangSmith is architecturally excluded (cloud-only; PII risk for banking data).
See docs/engineering_justification.md for rationale.
"""
from __future__ import annotations
import os
from typing import Optional

try:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler as _CallbackHandler
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False
    _CallbackHandler = None

from deployment.config import (
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
)


def _ensure_env() -> None:
    """Ensure Langfuse env vars are set so the v4 callback can auto-read them."""
    if LANGFUSE_PUBLIC_KEY:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", LANGFUSE_PUBLIC_KEY)
    if LANGFUSE_SECRET_KEY:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", LANGFUSE_SECRET_KEY)
    if LANGFUSE_HOST:
        os.environ.setdefault("LANGFUSE_HOST", LANGFUSE_HOST)


def _client() -> Optional[Langfuse]:
    if not _LANGFUSE_AVAILABLE or not LANGFUSE_PUBLIC_KEY:
        return None
    _ensure_env()
    return Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
    )


def get_langfuse_callback(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
):
    """
    Return a LangChain CallbackHandler, or None if Langfuse is not available /
    not configured (safe to use in Phase 2 where Langfuse isn't running yet).

    In Langfuse v4 the callback reads credentials from env vars automatically.
    session_id is forwarded as trace_id so all turns in a session are grouped.
    """
    if not _LANGFUSE_AVAILABLE or not LANGFUSE_PUBLIC_KEY:
        return None
    _ensure_env()
    try:
        # Langfuse v4 trace_id must be 32 lowercase hex chars (UUID without dashes)
        hex_id = session_id.replace("-", "").lower() if session_id else None

        if hex_id:
            # Ingest a trace-create event so Langfuse records session_id.
            # Without this, the v4 CallbackHandler only sets trace_id but not
            # session_id, so traces appear ungrouped in the Langfuse UI.
            import uuid as _uuid
            from datetime import datetime, timezone
            from langfuse.api.ingestion import TraceBody, TraceEvent
            _client().api.ingestion.batch(batch=[
                TraceEvent(
                    type="trace-create",
                    body=TraceBody(id=hex_id, session_id=hex_id, tags=tags),
                    id=str(_uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            ])

        trace_ctx = {"trace_id": hex_id} if hex_id else None
        return _CallbackHandler(trace_context=trace_ctx)
    except Exception:
        return None


def score_session(
    trace_id: str,
    score_name: str,
    value: float,
    comment: Optional[str] = None,
) -> None:
    """Post a numeric score to a Langfuse trace (used for RLHF feedback and RAG eval)."""
    client = _client()
    if client:
        try:
            client.create_score(
                trace_id=trace_id,
                name=score_name,
                value=value,
                comment=comment,
            )
        except Exception:
            pass


def flush() -> None:
    """Flush pending events to Langfuse (no-op if Langfuse is not configured)."""
    client = _client()
    if client:
        try:
            client.flush()
        except Exception:
            pass


# ── Dataset helpers (Phase 3 prompt-comparison evaluation) ────────────────────

def get_or_create_dataset(name: str) -> Optional[str]:
    """Create a Langfuse dataset if it doesn't exist; return its name (or None if unavailable)."""
    client = _client()
    if not client:
        return None
    try:
        client.create_dataset(name=name)
    except Exception:
        pass  # already exists — safe to ignore
    return name


def upload_dataset_item(
    dataset_name: str,
    input_text: str,
    expected_output: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Append one item to a Langfuse dataset."""
    client = _client()
    if not client:
        return
    try:
        client.create_dataset_item(
            dataset_name=dataset_name,
            input={"input": input_text},
            expected_output={"output": expected_output} if expected_output else None,
            metadata=metadata or {},
        )
    except Exception:
        pass


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None,
) -> None:
    """Alias for score_session — post a numeric score to a Langfuse trace."""
    score_session(trace_id=trace_id, score_name=name, value=value, comment=comment)
