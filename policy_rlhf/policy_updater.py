"""
Adaptation rules: analyse feedback and adjust agent behaviour.

Two layers of adaptation:
  1. Empathy prefix   — triggered when avg normalized rating < 0.6
  2. Adaptive policy  — LLM-generated instructions in data/rlhf/adaptive_policy.json,
                        populated by running scripts/run_rlhf_pipeline.py
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from deployment.config import DATA_DIR

STORE_PATH = DATA_DIR / "rlhf" / "feedback_store.json"
ADAPTIVE_POLICY_PATH = DATA_DIR / "rlhf" / "adaptive_policy.json"

_log = logging.getLogger(__name__)

# Prepended to the system prompt when recent ratings are low
EMPATHY_PREFIX = (
    "IMPORTANT — EMPATHY BOOST ACTIVE: Recent user feedback indicates responses "
    "have felt too transactional. Before answering, briefly acknowledge the "
    "customer's situation or concern in one warm sentence. Use reassuring, "
    "human language throughout — avoid bullet-point-only answers for emotional topics.\n\n"
)

_LLM_PROMPT = """\
You are a quality analyst for a banking AI chatbot that helps customers with loan applications.

Below are recent customer feedback comments rated 3 stars or below (out of 5).
Each comment reflects a specific failure in the chatbot's behaviour.

Low-rated comments:
{comments}

Already-active policy entries (do NOT duplicate or contradict these):
{existing_entries}

Analyse the comments and identify specific, repeatable behavioural failures.
For each distinct failure pattern supported by at least 2 comments:
  - Write a precise, actionable instruction the agent must follow
  - The instruction must be specific enough that following it eliminates the failure
  - Do not write vague instructions such as "be more helpful"
  - Do not create an entry about response speed or latency — that is an infrastructure concern

Return a JSON object with a single key "entries" containing an array:
{{
  "entries": [
    {{
      "id": "snake_case_unique_id",
      "instruction": "Specific agent instruction...",
      "trigger_comments": ["exact comment 1", "exact comment 2"]
    }}
  ]
}}

If no actionable patterns exist, return {{"entries": []}}.\
"""


def _normalize_rating(rating: float) -> float:
    """Normalize 1–5 star rating to 0–1.

    Uses (rating − 1) / 4 uniformly across the 1–5 range:
      1★ → 0.00  ·  2★ → 0.25  ·  3★ → 0.50  ·  4★ → 0.75  ·  5★ → 1.00

    Legacy entries with rating = 0 (old binary "not helpful") are mapped to 0.0.
    """
    if rating <= 0:
        return 0.0
    return (min(max(float(rating), 1.0), 5.0) - 1.0) / 4.0


def _load_store() -> list:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _load_adaptive_policy() -> list[dict]:
    if not ADAPTIVE_POLICY_PATH.exists():
        return []
    return json.loads(ADAPTIVE_POLICY_PATH.read_text(encoding="utf-8"))


def _save_adaptive_policy(entries: list[dict]) -> None:
    ADAPTIVE_POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADAPTIVE_POLICY_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2)
    )


def analyse_feedback(min_samples: int = 5) -> dict:
    """
    Analyse recent feedback records and return adaptation signals.

    Returns dict with suggested prompt or behaviour adjustments, plus the
    current adaptive policy entries for dashboard display.
    """
    store = _load_store()
    if len(store) < min_samples:
        return {"status": "insufficient_data", "count": len(store)}

    window = store[-20:]  # last 20 entries
    raw_ratings = [r["rating"] for r in window]
    normalized = [_normalize_rating(r) for r in raw_ratings]
    avg = sum(normalized) / len(normalized)

    comments = [
        {"rating": r["rating"], "comment": r["comment"], "ts": r.get("ts", "")[:16]}
        for r in window
        if r.get("comment", "").strip()
    ]

    signals = {
        "avg_rating": round(avg, 2),
        "avg_stars": round(avg * 4 + 1, 1),
        "sample_size": len(normalized),
        "comments": comments,
        "adaptive_policy_entries": _load_adaptive_policy(),
    }

    if avg < 0.6:
        signals["adapt"] = "increase_empathy"
        signals["action"] = "Inject empathy prefix in system prompt for next session"
    elif avg >= 0.85:
        signals["adapt"] = "maintain"
        signals["action"] = "Current behaviour performing well — no change needed"
    else:
        signals["adapt"] = "neutral"
        signals["action"] = (
            f"Avg {signals['avg_stars']}/5 — no adaptation triggered, "
            "ratings in acceptable range"
        )

    return signals


def update_adaptive_policy(comments: list[dict]) -> dict:
    """Call GPT-4o-mini to identify behavioural failure patterns in low-rated
    comments and merge the results into adaptive_policy.json.

    Only entries with source != "manual" are ever overwritten — human-authored
    entries are permanently protected from LLM modification.

    Returns a result dict:
      status    : "updated" | "skipped" | "llm_unavailable"
      changelog : list of human-readable strings describing what changed
    """
    low_rated = [
        c for c in comments
        if c.get("rating", 5) <= 3 and c.get("comment", "").strip()
    ]
    if len(low_rated) < 2:
        return {
            "status": "skipped",
            "reason": "fewer than 2 low-rated comments with text",
            "changelog": [],
        }

    existing = _load_adaptive_policy()
    existing_summary = (
        json.dumps(
            [{"id": e["id"], "instruction": e["instruction"]} for e in existing],
            indent=2,
        )
        if existing else "None"
    )
    formatted_comments = "\n".join(
        f"  [{c['rating']}★] {c['comment']}" for c in low_rated
    )

    prompt = _LLM_PROMPT.format(
        comments=formatted_comments,
        existing_entries=existing_summary,
    )

    try:
        from langchain_openai import ChatOpenAI
        from deployment.config import OPENAI_API_KEY, OPENAI_BASE_URL, SAFETY_MODEL

        kwargs: dict = {"api_key": OPENAI_API_KEY, "model": SAFETY_MODEL}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL

        llm = ChatOpenAI(**kwargs)
        response = llm.invoke(
            [{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        raw = json.loads(response.content)
        new_entries = raw.get("entries", [])
    except Exception as exc:
        _log.warning("LLM call for adaptive policy failed: %s", exc)
        return {"status": "llm_unavailable", "reason": str(exc), "changelog": []}

    now = datetime.utcnow().isoformat(timespec="seconds")
    existing_by_id = {e["id"]: e for e in existing}
    changelog: list[str] = []

    for entry in new_entries:
        eid = entry.get("id", "").strip()
        instruction = entry.get("instruction", "").strip()
        trigger_comments = entry.get("trigger_comments", [])
        if not eid or not instruction:
            continue

        if eid in existing_by_id:
            old = existing_by_id[eid]
            if old.get("source") == "manual":
                changelog.append(f"  PROTECTED  {eid}  (manual entry — not overwritten)")
                continue
            old["instruction"] = instruction
            old["trigger_comments"] = trigger_comments
            old["trigger_count"] = old.get("trigger_count", 1) + 1
            old["last_updated"] = now
            changelog.append(
                f"  UPDATED    {eid}  (trigger_count: {old['trigger_count']})"
            )
        else:
            existing_by_id[eid] = {
                "id": eid,
                "instruction": instruction,
                "trigger_comments": trigger_comments,
                "trigger_count": len(trigger_comments),
                "source": "llm_auto",
                "created": now,
                "last_updated": now,
                "active": True,
            }
            changelog.append(f"  ADDED      {eid}")

    _save_adaptive_policy(list(existing_by_id.values()))
    return {"status": "updated", "changelog": changelog}


def get_adapted_prompt(base_prompt: str) -> str:
    """Return base_prompt with feedback-driven prefixes applied.

    Stacking order (outermost first):
      1. Empathy prefix          — if recent avg normalized rating < 0.6
      2. Adaptive policy block   — active entries from adaptive_policy.json
      3. Base system prompt

    If adaptive_policy.json is empty or missing, behaviour is identical to
    the pre-RLHF baseline.
    """
    signal = analyse_feedback()
    additions: list[str] = []

    if signal.get("adapt") == "increase_empathy":
        additions.append(EMPATHY_PREFIX)

    active_entries = [e for e in _load_adaptive_policy() if e.get("active", True)]
    if active_entries:
        lines = ["ADAPTIVE POLICY (derived from customer feedback — follow strictly):"]
        for e in active_entries:
            lines.append(f"• {e['instruction']}")
        additions.append("\n".join(lines) + "\n\n")

    return "".join(additions) + base_prompt if additions else base_prompt
