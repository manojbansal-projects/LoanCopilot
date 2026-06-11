"""
Phase 7 RLHF pipeline — analyse feedback and log adaptation signals.

Usage:
    python scripts/run_rlhf_pipeline.py
"""
from policy_rlhf.policy_updater import analyse_feedback
import json


def main():
    signals = analyse_feedback()
    print(json.dumps(signals, indent=2))


if __name__ == "__main__":
    main()
