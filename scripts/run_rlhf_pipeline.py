"""
Phase 7 RLHF pipeline — analyse feedback and log adaptation signals.

Usage:
    python scripts/run_rlhf_pipeline.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_rlhf.policy_updater import analyse_feedback
from policy_rlhf.feedback_collector import _load_store
import json


def main():
    # ── Full record table ─────────────────────────────────────────────────────
    store = _load_store()
    print(f"Total feedback records: {len(store)}")
    if store:
        print()
        print(f"{'#':<4} {'Stars':<8} {'Turn':<6} {'Session':<10} {'Comment'}")
        print("-" * 72)
        for i, r in enumerate(store, 1):
            stars = "★" * r["rating"] + "☆" * (5 - r["rating"])
            comment = r.get("comment") or "(none)"
            session = r.get("session_id", "")[:8]
            turn = r.get("turn", "-")
            print(f"{i:<4} {stars:<8} {str(turn):<6} {session:<10} {comment}")

    # ── RLHF signal ───────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("RLHF Signal (last 20 records)")
    print("=" * 72)
    signals = analyse_feedback()

    if "status" in signals:
        print(f"Status      : {signals['status']} ({signals['count']} records — need 5+)")
    else:
        print(f"Avg rating  : {signals['avg_stars']} / 5  "
              f"(normalised: {signals['avg_rating']})")
        print(f"Sample size : {signals['sample_size']}")
        print(f"Adaptation  : {signals['adapt']}")
        print(f"Action      : {signals['action']}")

        comments = signals.get("comments", [])
        if comments:
            print()
            print("Qualitative comments:")
            for c in comments:
                stars = "★" * c["rating"] + "☆" * (5 - c["rating"])
                print(f"  [{stars}]  {c['comment']}")
        else:
            print()
            print("Qualitative comments: (none provided)")


if __name__ == "__main__":
    main()
