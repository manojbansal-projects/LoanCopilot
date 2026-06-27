"""Unit tests for policy_rlhf/policy_updater.py"""
import json
from unittest.mock import MagicMock, patch
import pytest
from policy_rlhf.policy_updater import (
    _normalize_rating, analyse_feedback, get_adapted_prompt, EMPATHY_PREFIX,
    _load_adaptive_policy, _save_adaptive_policy, update_adaptive_policy,
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


class TestLoadAdaptivePolicy:
    def test_returns_empty_list_when_file_missing(self, empty_adaptive_policy):
        empty_adaptive_policy.unlink()
        result = _load_adaptive_policy()
        assert result == []

    def test_returns_entries_from_file(self, empty_adaptive_policy):
        entries = [{"id": "test", "instruction": "Do X", "active": True,
                    "source": "llm_auto", "trigger_count": 1}]
        empty_adaptive_policy.write_text(json.dumps(entries))
        result = _load_adaptive_policy()
        assert len(result) == 1
        assert result[0]["id"] == "test"

    def test_only_active_entries_used_in_prompt(
            self, empty_feedback_store, empty_adaptive_policy):
        entries = [
            {"id": "active_one", "instruction": "Do A", "active": True,
             "source": "llm_auto", "trigger_count": 1},
            {"id": "inactive_one", "instruction": "Do B", "active": False,
             "source": "llm_auto", "trigger_count": 1},
        ]
        empty_adaptive_policy.write_text(json.dumps(entries))
        # No feedback records → empathy won't fire; only policy entries matter
        result = get_adapted_prompt("BASE")
        assert "Do A" in result
        assert "Do B" not in result


class TestUpdateAdaptivePolicy:
    _low_comments = [
        {"rating": 2, "comment": "already provided the name, why ask again"},
        {"rating": 2, "comment": "I already told it my income but it asked me again"},
    ]

    def test_skips_when_fewer_than_two_low_rated_comments(self, empty_adaptive_policy):
        result = update_adaptive_policy([{"rating": 2, "comment": "one comment"}])
        assert result["status"] == "skipped"
        assert json.loads(empty_adaptive_policy.read_text()) == []

    def test_skips_when_comments_have_no_text(self, empty_adaptive_policy):
        comments = [{"rating": 1, "comment": ""}, {"rating": 2, "comment": "   "}]
        result = update_adaptive_policy(comments)
        assert result["status"] == "skipped"

    def test_adds_new_entry_from_llm(self, empty_adaptive_policy):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "entries": [{
                "id": "no_redundant_questions",
                "instruction": "Do not re-ask for information already provided.",
                "trigger_comments": self._low_comments[0]["comment"],
            }]
        })
        with patch("langchain_openai.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = mock_response
            result = update_adaptive_policy(self._low_comments)
        assert result["status"] == "updated"
        assert any("ADDED" in line for line in result["changelog"])
        saved = json.loads(empty_adaptive_policy.read_text())
        assert len(saved) == 1
        assert saved[0]["id"] == "no_redundant_questions"
        assert saved[0]["source"] == "llm_auto"
        assert saved[0]["active"] is True

    def test_updates_existing_llm_entry(self, empty_adaptive_policy):
        existing = [{
            "id": "no_redundant_questions",
            "instruction": "Old instruction.",
            "trigger_comments": [],
            "trigger_count": 1,
            "source": "llm_auto",
            "created": "2026-01-01T00:00:00",
            "last_updated": "2026-01-01T00:00:00",
            "active": True,
        }]
        empty_adaptive_policy.write_text(json.dumps(existing))
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "entries": [{
                "id": "no_redundant_questions",
                "instruction": "Updated instruction.",
                "trigger_comments": [],
            }]
        })
        with patch("langchain_openai.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = mock_response
            result = update_adaptive_policy(self._low_comments)
        assert result["status"] == "updated"
        assert any("UPDATED" in line for line in result["changelog"])
        saved = json.loads(empty_adaptive_policy.read_text())
        assert saved[0]["trigger_count"] == 2
        assert saved[0]["instruction"] == "Updated instruction."

    def test_never_overwrites_manual_entry(self, empty_adaptive_policy):
        existing = [{
            "id": "compliance_rule",
            "instruction": "Always add RBI disclaimer.",
            "trigger_comments": [],
            "trigger_count": 0,
            "source": "manual",
            "created": "2026-01-01T00:00:00",
            "last_updated": "2026-01-01T00:00:00",
            "active": True,
        }]
        empty_adaptive_policy.write_text(json.dumps(existing))
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "entries": [{
                "id": "compliance_rule",
                "instruction": "LLM trying to overwrite manual entry.",
                "trigger_comments": [],
            }]
        })
        with patch("langchain_openai.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = mock_response
            result = update_adaptive_policy(self._low_comments)
        saved = json.loads(empty_adaptive_policy.read_text())
        assert saved[0]["instruction"] == "Always add RBI disclaimer."
        assert any("PROTECTED" in line for line in result["changelog"])

    def test_graceful_fallback_on_llm_error(self, empty_adaptive_policy):
        with patch("langchain_openai.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.side_effect = Exception("API budget exceeded")
            result = update_adaptive_policy(self._low_comments)
        assert result["status"] == "llm_unavailable"
        assert "API budget exceeded" in result["reason"]
        assert json.loads(empty_adaptive_policy.read_text()) == []


class TestGetAdaptedPromptWithPolicy:
    BASE = "You are a loan copilot."

    def test_active_policy_instructions_prepended(
            self, empty_feedback_store, empty_adaptive_policy):
        entries = [{"id": "rule_1", "instruction": "Always show EMI.",
                    "active": True, "source": "llm_auto", "trigger_count": 2}]
        empty_adaptive_policy.write_text(json.dumps(entries))
        result = get_adapted_prompt(self.BASE)
        assert "ADAPTIVE POLICY" in result
        assert "Always show EMI." in result
        assert result.endswith(self.BASE)

    def test_inactive_entries_excluded(
            self, empty_feedback_store, empty_adaptive_policy):
        entries = [{"id": "rule_1", "instruction": "Should not appear.",
                    "active": False, "source": "llm_auto", "trigger_count": 2}]
        empty_adaptive_policy.write_text(json.dumps(entries))
        result = get_adapted_prompt(self.BASE)
        assert "Should not appear." not in result

    def test_empathy_and_policy_stacked_correctly(
            self, empty_feedback_store, empty_adaptive_policy):
        records = [
            {"id": f"r{i}", "session_id": "s", "turn": i,
             "feedback_type": "per_turn", "response_preview": "",
             "rating": 1, "comment": "", "ts": "2026-01-01T00:00:00"}
            for i in range(10)
        ]
        empty_feedback_store.write_text(json.dumps(records))
        entries = [{"id": "rule_1", "instruction": "Be concise.",
                    "active": True, "source": "llm_auto", "trigger_count": 2}]
        empty_adaptive_policy.write_text(json.dumps(entries))
        result = get_adapted_prompt(self.BASE)
        empathy_pos = result.index(EMPATHY_PREFIX)
        policy_pos = result.index("ADAPTIVE POLICY")
        base_pos = result.index(self.BASE)
        assert empathy_pos < policy_pos < base_pos
