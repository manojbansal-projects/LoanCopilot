"""Collect yes/no user feedback at the end of each conversation turn."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path
from safety.pii_filter import mask
from deployment.config import DATA_DIR

STORE_PATH = DATA_DIR / "rlhf" / "feedback_store.json"


def record_feedback(
    session_id: str,
    turn: int,
    agent_response: str,
    rating: int,          # 1 = helpful, 0 = not helpful
    comment: str = "",
) -> None:
    """Append a feedback record (PII-masked) to the persistent JSON store."""
    entry = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "turn": turn,
        "response_preview": mask(agent_response[:200]),
        "rating": rating,
        "comment": mask(comment),
        "ts": datetime.utcnow().isoformat(),
    }
    store = _load_store()
    store.append(entry)
    STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2))


def _load_store() -> list:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))
