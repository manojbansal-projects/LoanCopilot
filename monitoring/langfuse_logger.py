"""
Langfuse self-hosted integration — single observability platform for this project.
Provides a LangChain CallbackHandler + helper for session scoring.

LangSmith is architecturally excluded (cloud-only; PII risk for banking data).
See docs/engineering_justification.md for rationale.
"""
from __future__ import annotations
import os
from typing import Optional

try:
    from langfuse import Langfuse
    from langfuse.callback import CallbackHandler as _CallbackHandler
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False
    _CallbackHandler = None

from deployment.config import (
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
)


def _client():
    if not _LANGFUSE_AVAILABLE:
        return None
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
    """
    if not _LANGFUSE_AVAILABLE or not LANGFUSE_PUBLIC_KEY:
        return None
    try:
        return _CallbackHandler(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
        )
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
        client.score(trace_id=trace_id, name=score_name, value=value, comment=comment)


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
