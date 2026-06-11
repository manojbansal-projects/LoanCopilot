"""
Adaptation rules: analyse feedback and adjust agent behaviour.
Phase 7 target: implement 2 rules; third rule (income-verification rationale) is stretch goal.
"""
from __future__ import annotations
import json
from deployment.config import DATA_DIR

STORE_PATH = DATA_DIR / "rlhf" / "feedback_store.json"


def analyse_feedback(min_samples: int = 5) -> dict:
    """
    Analyse recent feedback records and return adaptation signals.
    Returns dict with suggested prompt or behaviour adjustments.
    """
    # TODO (Phase 7): implement sliding-window analysis
    store = _load_store()
    if len(store) < min_samples:
        return {"status": "insufficient_data", "count": len(store)}

    ratings = [r["rating"] for r in store[-20:]]  # last 20 entries
    avg = sum(ratings) / len(ratings)

    signals = {"avg_rating": round(avg, 2), "sample_size": len(ratings)}

    # Rule 1: If avg < 0.6, suggest switching to more empathetic tone
    if avg < 0.6:
        signals["adapt"] = "increase_empathy"
        signals["action"] = "Inject empathy prefix in system prompt for next session"

    # Rule 2: If avg >= 0.85, log positive reinforcement
    elif avg >= 0.85:
        signals["adapt"] = "maintain"
        signals["action"] = "Current behaviour performing well — no change needed"

    return signals


def _load_store() -> list:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))
