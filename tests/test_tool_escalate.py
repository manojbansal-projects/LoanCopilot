"""Unit tests for tools/tool_escalate.py"""
import json
import pytest
from tools.tool_escalate import (
    _validate_mobile, _validate_email,
    _build_rm_briefing, generate_escalation_summary,
    _persist_escalation,
)


class TestValidateMobile:
    @pytest.mark.parametrize("number,expected_valid,expected_clean", [
        ("9876543210",   True,  "9876543210"),
        ("8765432109",   True,  "8765432109"),
        ("6543210987",   True,  "6543210987"),
        ("+919876543210", True, "9876543210"),
        ("919876543210",  True, "9876543210"),
        ("09876543210",   True, "9876543210"),
        ("98765 43210",   True, "9876543210"),   # spaces stripped
        ("9876-543-210",  True, "9876543210"),   # hyphens stripped
    ])
    def test_valid_numbers(self, number, expected_valid, expected_clean):
        valid, clean = _validate_mobile(number)
        assert valid is True, f"Expected valid for {number!r}"
        assert clean == expected_clean

    @pytest.mark.parametrize("number", [
        "1234567890",   # starts with 1 — not a valid mobile
        "5432109876",   # starts with 5
        "98765",        # too short
        "987654321011", # too long (not a valid prefix format)
        "abcdefghij",
        "",
    ])
    def test_invalid_numbers(self, number):
        valid, _ = _validate_mobile(number)
        assert valid is False, f"Expected invalid for {number!r}"


class TestValidateEmail:
    @pytest.mark.parametrize("email", [
        "user@example.com",
        "first.last@bank.co.in",
        "user+tag@gmail.com",
        "arjun@wipro.com",
    ])
    def test_valid_emails(self, email):
        assert _validate_email(email) is True

    @pytest.mark.parametrize("email", [
        "notanemail",
        "missing@tld",
        "@nodomain.com",
        "no-at-sign",
        "",
    ])
    def test_invalid_emails(self, email):
        assert _validate_email(email) is False


class TestBuildRMBriefing:
    def _briefing(self, **kwargs):
        defaults = dict(
            customer_name="Arjun Sharma",
            callback_number="9845012345",
            customer_email="arjun@wipro.com",
            gender="male",
            preferred_contact_time="weekdays 11 AM–1 PM",
            loan_product="car_loan",
            loan_amount=28_00_000,
            tenure_months=84,
            monthly_income=95_000,
            existing_emi_obligations=0,
            age=32,
            employment_type="salaried",
            credit_score=740,
            customer_intent="Purchase Toyota Fortuner on-road ₹28L",
            escalation_reason="Loan amount ₹28L exceeds car loan ceiling ₹20L",
            conversation_summary="Customer confirmed income and CIBIL",
            escalation_id="ABCD1234",
            timestamp="2026-06-13 14:30:00",
        )
        defaults.update(kwargs)
        return _build_rm_briefing(**defaults)

    def test_contains_customer_name(self):
        assert "Arjun Sharma" in self._briefing()

    def test_male_salutation(self):
        assert "Mr." in self._briefing(gender="male")

    def test_female_salutation(self):
        assert "Ms." in self._briefing(gender="female", customer_name="Meera Iyer")

    def test_no_salutation_for_other_gender(self):
        b = self._briefing(gender="other")
        assert "Mr." not in b
        assert "Ms." not in b

    def test_escalation_id_present(self):
        assert "ABCD1234" in self._briefing()

    def test_loan_amount_formatted(self):
        b = self._briefing(loan_amount=28_00_000)
        assert "28.0 L" in b or "₹28" in b

    def test_talking_points_present(self):
        b = self._briefing(loan_product="car_loan")
        assert "proforma" in b.lower() or "invoice" in b.lower()

    def test_disclaimer_present(self):
        assert "indicative" in self._briefing().lower()

    def test_conversation_summary_included(self):
        assert "Customer confirmed income and CIBIL" in self._briefing()


class TestGenerateEscalationSummaryTool:
    _VALID_ARGS = dict(
        customer_intent="Home loan for 3BHK in Pune",
        loan_product="home_loan",
        loan_amount=2_20_00_000,
        monthly_income=1_80_000,
        escalation_reason="Loan exceeds ceiling",
        customer_name="Meera Iyer",
        callback_number="7654321098",
        customer_email="meera@hdfcbank.com",
        age=38,
        employment_type="salaried",
        credit_score=785,
        tenure_months=300,
        gender="female",
        preferred_contact_time="Saturday mornings",
    )

    def test_missing_callback_number(self):
        args = dict(self._VALID_ARGS)
        args["callback_number"] = ""
        r = generate_escalation_summary.invoke(args)
        assert r["escalation_saved"] is False
        assert any("callback_number" in e for e in r["validation_errors"])

    def test_invalid_mobile(self):
        args = dict(self._VALID_ARGS)
        args["callback_number"] = "1234567890"
        r = generate_escalation_summary.invoke(args)
        assert r["escalation_saved"] is False
        assert any("callback_number" in e for e in r["validation_errors"])

    def test_missing_email(self):
        args = dict(self._VALID_ARGS)
        args["customer_email"] = ""
        r = generate_escalation_summary.invoke(args)
        assert r["escalation_saved"] is False
        assert any("customer_email" in e for e in r["validation_errors"])

    def test_invalid_email(self):
        args = dict(self._VALID_ARGS)
        args["customer_email"] = "not-an-email"
        r = generate_escalation_summary.invoke(args)
        assert r["escalation_saved"] is False

    def test_valid_input_saves_escalation(self, monkeypatch):
        monkeypatch.setattr(
            "tools.tool_escalate._persist_escalation",
            lambda data_dir, packet: None,  # no-op — avoid real file write
        )
        r = generate_escalation_summary.invoke(self._VALID_ARGS)
        assert r["escalation_saved"] is True
        assert "escalation_id" in r
        assert "rm_briefing" in r
        assert "customer_message" in r

    def test_customer_message_contains_last_four_digits(self, monkeypatch):
        monkeypatch.setattr(
            "tools.tool_escalate._persist_escalation",
            lambda data_dir, packet: None,
        )
        r = generate_escalation_summary.invoke(self._VALID_ARGS)
        assert "1098" in r["customer_message"]   # last 4 digits of 7654321098

    def test_both_missing_triggers_two_errors(self):
        args = dict(self._VALID_ARGS)
        args["callback_number"] = ""
        args["customer_email"] = ""
        r = generate_escalation_summary.invoke(args)
        assert len(r["validation_errors"]) >= 2

    def test_retry_instruction_present_on_failure(self):
        args = dict(self._VALID_ARGS)
        args["callback_number"] = ""
        r = generate_escalation_summary.invoke(args)
        assert "retry_instruction" in r


class TestPersistEscalation:
    def test_creates_file_if_missing(self, tmp_path):
        data_dir = tmp_path
        rlhf_dir = data_dir / "rlhf"
        rlhf_dir.mkdir(parents=True)
        packet = {"escalation_id": "XY123", "customer_name": "Test"}
        _persist_escalation(data_dir, packet)
        path = rlhf_dir / "escalations.json"
        assert path.exists()
        records = json.loads(path.read_text())
        assert len(records) == 1
        assert records[0]["escalation_id"] == "XY123"

    def test_appends_to_existing(self, tmp_path):
        data_dir = tmp_path
        rlhf_dir = data_dir / "rlhf"
        rlhf_dir.mkdir(parents=True)
        path = rlhf_dir / "escalations.json"
        path.write_text(json.dumps([{"escalation_id": "FIRST"}]))
        _persist_escalation(data_dir, {"escalation_id": "SECOND"})
        records = json.loads(path.read_text())
        assert len(records) == 2
        assert records[1]["escalation_id"] == "SECOND"
