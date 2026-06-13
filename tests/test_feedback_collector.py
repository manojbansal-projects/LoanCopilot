"""Unit tests for policy_rlhf/feedback_collector.py"""
import json
import pytest
from policy_rlhf.feedback_collector import record_feedback


class TestRecordFeedback:
    def test_record_written_to_store(self, empty_feedback_store):
        record_feedback("sess-1", 1, "Great answer", 5)
        records = json.loads(empty_feedback_store.read_text())
        assert len(records) == 1

    def test_record_fields(self, empty_feedback_store):
        record_feedback("sess-1", 2, "Some response", 4, comment="Helpful")
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert rec["session_id"] == "sess-1"
        assert rec["turn"] == 2
        assert rec["rating"] == 4
        assert rec["comment"] == "Helpful"
        assert rec["feedback_type"] == "per_turn"
        assert "id" in rec
        assert "ts" in rec

    def test_session_feedback_type(self, empty_feedback_store):
        record_feedback("sess-2", 0, "Final review", 3, feedback_type="session")
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert rec["feedback_type"] == "session"

    def test_rating_clamped_low(self, empty_feedback_store):
        record_feedback("s", 0, "resp", 0)   # 0 → clamped to 1
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert rec["rating"] == 1

    def test_rating_clamped_high(self, empty_feedback_store):
        record_feedback("s", 0, "resp", 10)  # 10 → clamped to 5
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert rec["rating"] == 5

    def test_pii_in_response_preview_masked(self, empty_feedback_store):
        record_feedback("s", 0, "Call me at 9876543210 thanks", 4)
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert "9876543210" not in rec["response_preview"]
        assert "[MOBILE REDACTED]" in rec["response_preview"]

    def test_pii_in_comment_masked(self, empty_feedback_store):
        record_feedback("s", 0, "ok", 3, comment="My PAN is ABCDE1234F")
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert "ABCDE1234F" not in rec["comment"]
        assert "[PAN REDACTED]" in rec["comment"]

    def test_multiple_records_appended(self, empty_feedback_store):
        for i in range(5):
            record_feedback("s", i, f"response {i}", 3 + i % 3)
        records = json.loads(empty_feedback_store.read_text())
        assert len(records) == 5

    def test_response_preview_truncated_at_200(self, empty_feedback_store):
        long_response = "x" * 500
        record_feedback("s", 0, long_response, 5)
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert len(rec["response_preview"]) <= 200

    def test_empty_comment_stored_as_empty_string(self, empty_feedback_store):
        record_feedback("s", 0, "resp", 4)
        rec = json.loads(empty_feedback_store.read_text())[0]
        assert rec["comment"] == ""
