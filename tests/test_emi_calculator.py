"""Unit tests for tools/emi_calculator.py"""
import pytest
from tools.emi_calculator import calculate_emi


def _invoke(principal, rate, tenure):
    return calculate_emi.invoke({"principal": principal,
                                 "annual_rate_percent": rate,
                                 "tenure_months": tenure})


class TestEMIFormula:
    def test_standard_home_loan(self):
        """50L @ 9% for 20 years — well-known benchmark."""
        r = _invoke(50_00_000, 9.0, 240)
        assert r["emi"] == pytest.approx(44_986.0, abs=5), "EMI mismatch for 50L/9%/20yr"
        assert r["principal"] == 50_00_000
        assert r["tenure_months"] == 240

    def test_total_payable_equals_emi_times_tenure(self):
        r = _invoke(10_00_000, 10.0, 60)
        assert r["total_payable"] == pytest.approx(r["emi"] * 60, rel=1e-4)

    def test_total_interest_is_payable_minus_principal(self):
        r = _invoke(10_00_000, 10.0, 60)
        assert r["total_interest"] == pytest.approx(r["total_payable"] - r["principal"], abs=1)

    def test_zero_interest_rate(self):
        """Zero rate → EMI = principal / tenure."""
        r = _invoke(12_00_000, 0.0, 12)
        assert r["emi"] == pytest.approx(1_00_000.0, abs=0.01)
        assert r["total_interest"] == pytest.approx(0.0, abs=0.01)

    def test_single_month_tenure(self):
        """Single-month loan → EMI ≈ principal + one month's interest."""
        r = _invoke(1_00_000, 12.0, 1)
        expected_emi = 1_00_000 * (0.01) * (1.01) / (1.01 - 1)
        assert r["emi"] == pytest.approx(expected_emi, rel=1e-4)

    def test_high_rate_personal_loan(self):
        """Personal loan edge: 24% p.a. for 5 years — total payable ~73% above principal."""
        r = _invoke(5_00_000, 24.0, 60)
        assert r["emi"] > 0
        assert r["total_payable"] > r["principal"] * 1.5

    def test_keys_present(self):
        r = _invoke(10_00_000, 9.0, 120)
        for key in ("emi", "total_payable", "total_interest", "principal",
                    "annual_rate_percent", "tenure_months"):
            assert key in r

    def test_emi_rounded_to_two_decimals(self):
        r = _invoke(7_50_000, 8.75, 180)
        emi_str = str(r["emi"])
        decimal_places = len(emi_str.split(".")[-1]) if "." in emi_str else 0
        assert decimal_places <= 2


class TestEMIEdgeCases:
    def test_zero_principal_returns_error(self):
        r = _invoke(0, 9.0, 120)
        assert "error" in r

    def test_negative_principal_returns_error(self):
        r = _invoke(-1_00_000, 9.0, 120)
        assert "error" in r

    def test_zero_tenure_returns_error(self):
        r = _invoke(10_00_000, 9.0, 0)
        assert "error" in r

    def test_negative_tenure_returns_error(self):
        r = _invoke(10_00_000, 9.0, -12)
        assert "error" in r
