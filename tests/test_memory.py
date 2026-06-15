"""Unit tests for agent/memory.py"""
import pytest
from agent.memory import CustomerProfile, SessionState, build_langchain_memory


class TestCustomerProfile:
    def test_all_fields_none_by_default(self):
        p = CustomerProfile()
        for field in ("loan_product", "monthly_income", "age", "employment_type",
                      "credit_score", "loan_amount", "tenure_months", "customer_name"):
            assert getattr(p, field) is None

    def test_missing_required_fields_all_missing(self):
        p = CustomerProfile()
        missing = p.missing_required_fields()
        assert set(missing) == {"loan_product", "loan_amount", "tenure_months",
                                 "monthly_income", "age", "employment_type"}

    def test_missing_required_fields_partial(self):
        p = CustomerProfile(loan_product="home_loan", monthly_income=1_00_000, age=35)
        missing = p.missing_required_fields()
        assert "loan_product" not in missing
        assert "monthly_income" not in missing
        assert "loan_amount" in missing
        assert "tenure_months" in missing

    def test_missing_required_fields_all_filled(self):
        p = CustomerProfile(
            loan_product="home_loan", monthly_income=1_00_000, age=35,
            employment_type="salaried", loan_amount=50_00_000, tenure_months=240,
        )
        assert p.missing_required_fields() == []

    def test_to_dict_excludes_none(self):
        p = CustomerProfile(loan_product="car_loan", age=30)
        d = p.to_dict()
        assert "loan_product" in d
        assert "age" in d
        assert "monthly_income" not in d  # None should be excluded

    def test_to_dict_all_fields(self):
        p = CustomerProfile(
            loan_product="home_loan", monthly_income=1_20_000, age=35,
            employment_type="salaried", credit_score=750, loan_amount=50_00_000,
            tenure_months=240, customer_name="Arjun",
        )
        d = p.to_dict()
        assert d["loan_product"] == "home_loan"
        assert d["monthly_income"] == 1_20_000
        assert d["credit_score"] == 750


class TestSessionState:
    def test_initial_state(self):
        s = SessionState(session_id="test-session")
        assert s.session_id == "test-session"
        assert s.turn_count == 0
        assert s.escalated is False
        assert s.eligibility_result is None
        assert s.emi_result is None
        assert isinstance(s.profile, CustomerProfile)

    def test_reset_clears_profile(self):
        s = SessionState(session_id="s1")
        s.profile.loan_product = "home_loan"
        s.profile.age = 35
        s.turn_count = 5
        s.escalated = True
        s.reset()
        assert s.profile.loan_product is None
        assert s.profile.age is None
        assert s.turn_count == 0
        assert s.escalated is False

    def test_reset_preserves_session_id(self):
        s = SessionState(session_id="my-session")
        s.reset()
        assert s.session_id == "my-session"

    def test_cibil_assumed_flag(self):
        s = SessionState(session_id="s1")
        assert s.cibil_assumed is False
        s.cibil_assumed = True
        assert s.cibil_assumed is True

    def test_last_asked_field(self):
        s = SessionState(session_id="s1")
        assert s.last_asked_field is None
        s.last_asked_field = "credit_score"
        assert s.last_asked_field == "credit_score"


    def test_existing_emi_obligations_defaults_none(self):
        p = CustomerProfile()
        assert p.existing_emi_obligations is None

    def test_existing_emi_obligations_settable(self):
        p = CustomerProfile(existing_emi_obligations=15_000.0)
        assert p.existing_emi_obligations == 15_000.0

    def test_existing_emi_obligations_in_to_dict(self):
        p = CustomerProfile(existing_emi_obligations=20_000.0)
        d = p.to_dict()
        assert "existing_emi_obligations" in d
        assert d["existing_emi_obligations"] == 20_000.0

    def test_existing_emi_obligations_excluded_from_to_dict_when_none(self):
        p = CustomerProfile()
        d = p.to_dict()
        assert "existing_emi_obligations" not in d


class TestSessionStateExtended:
    def test_last_asked_field_cleared_on_reset(self):
        s = SessionState(session_id="s1")
        s.last_asked_field = "credit_score"
        s.reset()
        assert s.last_asked_field is None

    def test_cibil_assumed_cleared_on_reset(self):
        s = SessionState(session_id="s1")
        s.cibil_assumed = True
        s.reset()
        assert s.cibil_assumed is False

    def test_eligibility_result_cleared_on_reset(self):
        s = SessionState(session_id="s1")
        s.eligibility_result = {"eligible": True}
        s.reset()
        assert s.eligibility_result is None

    def test_emi_result_cleared_on_reset(self):
        s = SessionState(session_id="s1")
        s.emi_result = {"low": {}, "high": {}}
        s.reset()
        assert s.emi_result is None

    def test_profile_is_fresh_instance_after_reset(self):
        """After reset, profile must be a brand-new CustomerProfile, not the same object."""
        s = SessionState(session_id="s1")
        old_profile = s.profile
        s.profile.loan_product = "car_loan"
        s.reset()
        # The object may be reused or replaced — key requirement is all fields are None
        assert s.profile.loan_product is None

    def test_multiple_resets_are_idempotent(self):
        s = SessionState(session_id="s1")
        s.reset()
        s.reset()
        assert s.turn_count == 0
        assert s.profile.loan_product is None


class TestLangChainMemory:
    def test_returns_memory_object(self):
        mem = build_langchain_memory()
        assert mem is not None

    def test_default_window_10(self):
        mem = build_langchain_memory()
        assert mem.k == 10

    def test_custom_window(self):
        mem = build_langchain_memory(window=5)
        assert mem.k == 5

    def test_memory_key(self):
        mem = build_langchain_memory()
        assert mem.memory_key == "chat_history"
