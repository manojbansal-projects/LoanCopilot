"""Unit tests for policy_rlhf/policy_checker.py"""
import pytest
from policy_rlhf.policy_checker import check_response, HARD_RULES


class TestNoRatePromise:
    def test_bare_rate_without_indicative_fails(self):
        violations = check_response("The interest rate is 8.5% for your loan.")
        ids = [v["rule_id"] for v in violations]
        assert "no_rate_promise" in ids

    def test_rate_with_indicative_passes(self):
        violations = check_response("The indicative rate is 8.5%–9.5% p.a.")
        ids = [v["rule_id"] for v in violations]
        assert "no_rate_promise" not in ids

    def test_rate_with_current_rate_passes(self):
        violations = check_response("current rate is around 9%")
        ids = [v["rule_id"] for v in violations]
        assert "no_rate_promise" not in ids

    def test_no_percent_sign_passes(self):
        violations = check_response("You are eligible for a home loan.")
        ids = [v["rule_id"] for v in violations]
        assert "no_rate_promise" not in ids


class TestNoApprovalGuarantee:
    def test_guaranteed_fails(self):
        violations = check_response("Your loan is guaranteed to be approved.")
        ids = [v["rule_id"] for v in violations]
        assert "no_approval_guarantee" in ids

    def test_will_be_approved_fails(self):
        violations = check_response("You will be approved for this loan.")
        ids = [v["rule_id"] for v in violations]
        assert "no_approval_guarantee" in ids

    def test_indicative_language_passes(self):
        violations = check_response(
            "Based on the indicative assessment, you appear eligible subject to credit appraisal."
        )
        ids = [v["rule_id"] for v in violations]
        assert "no_approval_guarantee" not in ids


class TestNoPIIInResponse:
    def test_aadhaar_word_in_response_fails(self):
        violations = check_response("Please share your aadhaar number with us.")
        ids = [v["rule_id"] for v in violations]
        assert "no_pii_in_response" in ids

    def test_pan_card_number_fails(self):
        violations = check_response("Your pan card number is required.")
        ids = [v["rule_id"] for v in violations]
        assert "no_pii_in_response" in ids

    def test_account_number_fails(self):
        violations = check_response("Please provide your account number.")
        ids = [v["rule_id"] for v in violations]
        assert "no_pii_in_response" in ids

    def test_clean_response_passes(self):
        violations = check_response(
            "To proceed, you will need to provide KYC documents at the branch."
        )
        assert violations == []


class TestAllRulesPass:
    def test_perfect_response_no_violations(self):
        response = (
            "Based on the details provided, you appear indicatively eligible for a "
            "home loan. The indicative rate range is 8.50%–9.50% p.a. — the exact "
            "rate will be confirmed at sanction after full credit appraisal. "
            "No approval is guaranteed at this stage."
        )
        violations = check_response(response)
        assert violations == []

    def test_violation_has_required_keys(self):
        violations = check_response("Your loan is guaranteed.")
        assert len(violations) > 0
        for v in violations:
            assert "rule_id" in v
            assert "description" in v


class TestRulesStructure:
    def test_all_rules_have_required_keys(self):
        for rule in HARD_RULES:
            assert "id" in rule
            assert "description" in rule
            assert "check" in rule
            assert callable(rule["check"])
