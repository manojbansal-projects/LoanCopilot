"""
Adaptation rules: analyse feedback and adjust agent behaviour.
Phase 7 target: implement 2 rules; third rule (income-verification rationale) is stretch goal.
"""
from __future__ import annotations
import json
from deployment.config import DATA_DIR

STORE_PATH = DATA_DIR / "rlhf" / "feedback_store.json"

# Prepended to the system prompt when recent ratings are low
EMPATHY_PREFIX = (
    "IMPORTANT — EMPATHY BOOST ACTIVE: Recent user feedback indicates responses "
    "have felt too transactional. Before answering, briefly acknowledge the "
    "customer's situation or concern in one warm sentence. Use reassuring, "
    "human language throughout — avoid bullet-point-only answers for emotional topics.\n\n"
)


def _normalize_rating(rating: float) -> float:
    """Normalize 1–5 star rating to 0–1.

    Uses (rating − 1) / 4 uniformly across the 1–5 range:
      1★ → 0.00  ·  2★ → 0.25  ·  3★ → 0.50  ·  4★ → 0.75  ·  5★ → 1.00

    Legacy entries with rating = 0 (old binary "not helpful") are mapped to 0.0.
    """
    if rating <= 0:
        return 0.0
    return (min(max(float(rating), 1.0), 5.0) - 1.0) / 4.0


def analyse_feedback(min_samples: int = 5) -> dict:
    """
    Analyse recent feedback records and return adaptation signals.

    All thresholds are applied to normalized ratings (0–1 scale) so they
    remain valid regardless of whether entries use the old 0/1 or new 1–5 scale.
    Returns dict with suggested prompt or behaviour adjustments.
    """
    store = _load_store()
    if len(store) < min_samples:
        return {"status": "insufficient_data", "count": len(store)}

    window = store[-20:]  # last 20 entries
    raw_ratings = [r["rating"] for r in window]
    normalized = [_normalize_rating(r) for r in raw_ratings]
    avg = sum(normalized) / len(normalized)

    # Collect non-empty comments from the window, tagged with their star rating
    comments = [
        {"rating": r["rating"], "comment": r["comment"], "ts": r.get("ts", "")[:16]}
        for r in window
        if r.get("comment", "").strip()
    ]

    signals = {
        "avg_rating": round(avg, 2),             # normalized 0–1 (for rule logic)
        "avg_stars": round(avg * 4 + 1, 1),      # 1.0–5.0 display value
        "sample_size": len(normalized),
        "comments": comments,                    # qualitative feedback from users
    }

    # Rule 1: If avg < 0.6, suggest switching to more empathetic tone
    if avg < 0.6:
        signals["adapt"] = "increase_empathy"
        signals["action"] = "Inject empathy prefix in system prompt for next session"

    # Rule 2: If avg >= 0.85, log positive reinforcement
    elif avg >= 0.85:
        signals["adapt"] = "maintain"
        signals["action"] = "Current behaviour performing well — no change needed"

    else:
        signals["adapt"] = "neutral"
        signals["action"] = (
            f"Avg {signals['avg_stars']}/5 — no adaptation triggered, ratings in acceptable range"
        )

    return signals


def get_adapted_prompt(base_prompt: str) -> str:
    """Return base_prompt, prepending an empathy prefix if recent feedback is poor.

    Call before building a new agent session so the adaptation takes effect
    from the first turn. If there is insufficient feedback data, returns the
    base prompt unchanged.
    """
    signal = analyse_feedback()
    if signal.get("adapt") == "increase_empathy":
        return EMPATHY_PREFIX + base_prompt
    return base_prompt


def _load_store() -> list:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))
