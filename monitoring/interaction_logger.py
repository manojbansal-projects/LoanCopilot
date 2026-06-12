"""Interaction logger — writes each chat turn to logs/interactions.log as JSONL.

All text fields are PII-masked before writing (CLAUDE.md constraint:
"All log writes must go through safety/pii_filter.mask() first").
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from deployment.config import LOG_DIR
from safety.pii_filter import mask

LOG_PATH = LOG_DIR / "interactions.log"


def log_interaction(
    session_id: str,
    turn: int,
    user_input: str,
    agent_response: str,
    latency_ms: int,
    intent: str = "IN_SCOPE",
    blocked: bool = False,
) -> None:
    """Append one PII-masked interaction record to interactions.log (JSONL format).

    Both user_input and agent_response are masked before writing.
    blocked=True means the safety gate rejected the query without calling the agent.
    """
    entry = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "session_id": session_id,
        "turn": turn,
        "intent": intent,
        "blocked": blocked,
        "latency_ms": latency_ms,
        "user_input_masked": mask(user_input[:300]),
        "response_preview_masked": mask(agent_response[:200]),
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent(n: int = 20) -> list[dict]:
    """Return the last n interaction records from the log (most-recent last)."""
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    records = []
    for line in lines[-n:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return records
