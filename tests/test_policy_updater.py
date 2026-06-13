"""Unit tests for policy_rlhf/policy_updater.py"""
import json
import pytest
from policy_rlhf.policy_updater import (
    _normalize_rating, analyse_feedback, get_adapted_prompt, EMPATHY_PREFIX,
)


class TestNormalizeRating:
    @pytest.mark.parametrize("raw,expected", [
        (1, 0.00),
        (2, 0.25),
        (3, 0.50),
        (4, 0.75),
        (5, 1.00),
        (0, 0.00),   # legacy binary "not helpful"
        (6, 1.00),   # clamped to max
    ])
    def test_normalization(self, raw, expected):
        assert _normalize_rating(raw) == pytest.approx(expected, abs=0.01)


class TestAnalyseFeedback:
    def test_insufficient_data(self, empty_feedback_store):
        result = analyse_feedback(min_samples=5)
        assert result["status"] == "insufficient_data"
        assert result["count"] == 0

    def test_insufficient_when_below_min_samples(self, empty_feedback_store):
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 4, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(3)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = analyse_feedback(min_samples=5)
        assert result["status"] == "insufficient_data"

    def test_low_ratings_trigger_empathy(self, empty_feedback_store):
        # All 1-star → avg_normalized = 0.0 → below 0.6 threshold
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 1, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = analyse_feedback(min_samples=5)
        assert result["adapt"] == "increase_empathy"

    def test_high_ratings_trigger_maintain(self, empty_feedback_store):
        # All 5-star → avg_normalized = 1.0 → above 0.85 threshold
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 5, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = analyse_feedback(min_samples=5)
        assert result["adapt"] == "maintain"

    def test_neutral_ratings_return_neutral(self, empty_feedback_store):
        # All 4-star → avg_normalized = 0.75 → between 0.6 and 0.85 → neutral
        # (3-star = 0.5 is below the 0.6 empathy threshold, so 4-star is used here)
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 4, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = analyse_feedback(min_samples=5)
        assert result["adapt"] == "neutral"

    def test_result_contains_avg_stars(self, populated_feedback_store):
        result = analyse_feedback(min_samples=5)
        assert "avg_stars" in result
        assert 1.0 <= result["avg_stars"] <= 5.0

    def test_comments_included_in_result(self, empty_feedback_store):
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 3, "comment": f"feedback {i}", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = analyse_feedback(min_samples=5)
        assert "comments" in result
        assert len(result["comments"]) > 0


class TestGetAdaptedPrompt:
    BASE = "You are a loan copilot."

    def test_no_data_returns_base_prompt(self, empty_feedback_store):
        result = get_adapted_prompt(self.BASE)
        assert result == self.BASE

    def test_low_ratings_prepend_empathy(self, empty_feedback_store):
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 1, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = get_adapted_prompt(self.BASE)
        assert result.startswith(EMPATHY_PREFIX)
        assert self.BASE in result

    def test_high_ratings_do_not_prepend(self, empty_feedback_store):
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 5, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        result = get_adapted_prompt(self.BASE)
        assert not result.startswith(EMPATHY_PREFIX)
        assert result == self.BASE
