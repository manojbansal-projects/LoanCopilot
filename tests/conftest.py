"""Shared pytest fixtures for the Loan Copilot test suite."""
import sys
import os
import json
import pytest

# Ensure project root is on the path so imports work without installing the package
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Create a minimal data/rlhf directory structure inside a temp dir."""
    rlhf = tmp_path / "data" / "rlhf"
    rlhf.mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def empty_feedback_store(tmp_data_dir, monkeypatch):
    """Patch STORE_PATH in feedback_collector and policy_updater to use tmp dir."""
    store_path = tmp_data_dir / "data" / "rlhf" / "feedback_store.json"
    import policy_rlhf.feedback_collector as fc
    import policy_rlhf.policy_updater as pu
    monkeypatch.setattr(fc, "STORE_PATH", store_path)
    monkeypatch.setattr(pu, "STORE_PATH", store_path)
    return store_path


@pytest.fixture()
def populated_feedback_store(empty_feedback_store):
    """Write 10 feedback records (mix of high/low ratings) to the store."""
    records = [
        {"id": f"r{i}", "session_id": "s1", "turn": i,
         "feedback_type": "per_turn", "response_preview": "OK",
         "rating": (5 if i % 2 == 0 else 2), "comment": "", "ts": "2026-01-01T00:00:00"}
        for i in range(10)
    ]
    empty_feedback_store.write_text(json.dumps(records))
    return empty_feedback_store
