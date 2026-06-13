"""Unit tests for agent/planner.py"""
import pytest
from agent.memory import CustomerProfile
from agent.planner import (
    next_question, next_field_and_question,
    is_ready_for_eligibility, COLLECTION_SEQUENCE,
)


def _full_profile():
    return CustomerProfile(
        loan_product="home_loan", loan_amount=50_00_000,
        tenure_months=240, monthly_income=1_50_000,
        age=35, employment_type="salaried", credit_score=750,
    )


class TestNextQuestion:
    def test_empty_profile_asks_first_field(self):
        p = CustomerProfile()
        q = next_question(p)
        assert q is not None
        # First item in COLLECTION_SEQUENCE is loan_product
        assert COLLECTION_SEQUENCE[0][0] == "loan_product"
        assert q == COLLECTION_SEQUENCE[0][1]

    def test_partial_profile_asks_next_missing(self):
        p = CustomerProfile(loan_product="home_loan")
        q = next_question(p)
        # Next field after loan_product is loan_amount
        assert q == COLLECTION_SEQUENCE[1][1]

    def test_complete_profile_returns_none(self):
        p = _full_profile()
        assert next_question(p) is None

    def test_sequence_exhausted_one_by_one(self):
        """Fill fields one at a time; each call returns the next question."""
        p = CustomerProfile()
        for field, expected_q in COLLECTION_SEQUENCE:
            returned_q = next_question(p)
            assert returned_q == expected_q
            setattr(p, field, "dummy")
        assert next_question(p) is None


class TestNextFieldAndQuestion:
    def test_empty_profile_returns_first_tuple(self):
        p = CustomerProfile()
        result = next_field_and_question(p)
        assert result is not None
        field, question = result
        assert field == COLLECTION_SEQUENCE[0][0]
        assert question == COLLECTION_SEQUENCE[0][1]

    def test_complete_profile_returns_none(self):
        assert next_field_and_question(_full_profile()) is None

    def test_returns_tuple_of_two(self):
        p = CustomerProfile()
        result = next_field_and_question(p)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestIsReadyForEligibility:
    def test_empty_profile_not_ready(self):
        assert is_ready_for_eligibility(CustomerProfile()) is False

    def test_partial_profile_not_ready(self):
        p = CustomerProfile(loan_product="home_loan", monthly_income=1_00_000)
        assert is_ready_for_eligibility(p) is False

    def test_all_required_fields_filled(self):
        p = CustomerProfile(
            loan_product="home_loan", loan_amount=50_00_000,
            tenure_months=240, monthly_income=1_50_000,
            age=35, employment_type="salaried",
        )
        assert is_ready_for_eligibility(p) is True

    def test_optional_credit_score_not_blocking(self):
        """credit_score is optional — readiness should not depend on it."""
        p = CustomerProfile(
            loan_product="home_loan", loan_amount=50_00_000,
            tenure_months=240, monthly_income=1_50_000,
            age=35, employment_type="salaried",
            credit_score=None,
        )
        assert is_ready_for_eligibility(p) is True
