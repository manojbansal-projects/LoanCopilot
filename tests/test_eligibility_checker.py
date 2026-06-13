"""Unit tests for tools/eligibility_checker.py"""
import pytest
from tools.eligibility_checker import check_eligibility, PRODUCT_LIMITS, RATE_BANDS
from deployment.config import ESCALATION_CEILINGS


def _check(**kwargs):
    defaults = dict(
        loan_product="home_loan",
        monthly_income=1_50_000,
        loan_amount=50_00_000,
        tenure_months=240,
        age=35,
        employment_type="salaried",
        credit_score=750,
        existing_emi_obligations=0.0,
    )
    defaults.update(kwargs)
    return check_eligibility.invoke(defaults)


class TestHappyPath:
    def test_eligible_home_loan(self):
        r = _check()
        assert r["eligible"] is True
        assert "PASS" in r["reason"]
        assert "escalate_to_rm" in r

    def test_rate_range_present(self):
        r = _check()
        assert "%" in r["indicative_rate_range"]
        lo, hi = RATE_BANDS["home_loan"]
        assert str(lo) in r["indicative_rate_range"]
        assert str(hi) in r["indicative_rate_range"]

    def test_foir_returned(self):
        r = _check()
        assert 0.0 <= r["foir"] <= 1.0

    def test_no_escalation_below_ceiling(self):
        r = _check(loan_amount=50_00_000)   # 50L < 1.5 Cr ceiling
        assert r["escalate_to_rm"] is False
        assert r.get("escalation_note") is None

    def test_escalation_above_ceiling(self):
        r = _check(loan_amount=2_00_00_000)  # 2 Cr > 1.5 Cr ceiling
        assert r["escalate_to_rm"] is True
        assert r["escalation_note"] is not None


class TestAgeChecks:
    def test_age_below_minimum(self):
        r = _check(age=20)
        assert r["eligible"] is False
        assert "Age" in r["reason"]

    def test_age_at_minimum(self):
        r = _check(age=21)
        assert r["eligible"] is True

    def test_age_above_maximum(self):
        r = _check(age=66)
        assert r["eligible"] is False
        assert "Age" in r["reason"]

    def test_age_at_maximum(self):
        r = _check(age=65)
        assert r["eligible"] is True


class TestCreditScoreChecks:
    def test_home_loan_score_below_700(self):
        r = _check(loan_product="home_loan", credit_score=699)
        assert r["eligible"] is False
        assert "Credit score" in r["reason"]

    def test_home_loan_score_at_700(self):
        r = _check(loan_product="home_loan", credit_score=700)
        assert r["eligible"] is True

    def test_personal_loan_score_below_720(self):
        r = _check(loan_product="personal_loan", monthly_income=80_000,
                   loan_amount=5_00_000, tenure_months=36, credit_score=715)
        assert r["eligible"] is False
        assert "Credit score" in r["reason"]

    def test_personal_loan_score_at_720(self):
        r = _check(loan_product="personal_loan", monthly_income=80_000,
                   loan_amount=5_00_000, tenure_months=36, credit_score=720)
        assert r["eligible"] is True

    def test_msme_loan_score_at_minimum(self):
        # Use 4L income + 120-month tenure so FOIR comfortably passes; isolates credit score check
        r = _check(loan_product="msme_loan", monthly_income=4_00_000,
                   loan_amount=50_00_000, tenure_months=120,
                   employment_type="business", credit_score=700)
        assert r["eligible"] is True


class TestAmountLimits:
    def test_amount_below_minimum(self):
        r = _check(loan_product="home_loan", loan_amount=4_00_000)  # min 5L
        assert r["eligible"] is False
        assert "Amount" in r["reason"]

    def test_amount_above_maximum(self):
        r = _check(loan_product="personal_loan", monthly_income=5_00_000,
                   loan_amount=41_00_000, tenure_months=36)  # max 40L
        assert r["eligible"] is False
        assert "Amount" in r["reason"]

    def test_car_loan_within_range(self):
        r = _check(loan_product="car_loan", loan_amount=10_00_000,
                   tenure_months=60, credit_score=750)
        assert r["eligible"] is True


class TestTenuireChecks:
    def test_tenure_exceeds_max(self):
        r = _check(loan_product="personal_loan", monthly_income=80_000,
                   loan_amount=5_00_000, tenure_months=72)  # max 60
        assert r["eligible"] is False
        assert "Tenure" in r["reason"]

    def test_tenure_at_max(self):
        r = _check(loan_product="personal_loan", monthly_income=80_000,
                   loan_amount=5_00_000, tenure_months=60)
        assert r["eligible"] is True


class TestFOIR:
    def test_foir_breach_standard_income(self):
        """Income ≤1L → FOIR limit 50%. Force breach via high existing EMI."""
        r = _check(monthly_income=80_000, loan_amount=30_00_000,
                   tenure_months=180, existing_emi_obligations=30_000)
        assert r["eligible"] is False
        assert "FOIR" in r["reason"]

    def test_foir_higher_limit_for_high_income(self):
        """Income > 1L → FOIR limit 55% — same obligation passes."""
        r = _check(monthly_income=1_50_000, loan_amount=30_00_000,
                   tenure_months=180, existing_emi_obligations=10_000)
        # At 1.5L income and 55% limit there's room
        assert r["foir"] <= 0.56  # verify limit applied correctly

    def test_existing_emi_included_in_foir(self):
        r1 = _check(existing_emi_obligations=0.0)
        r2 = _check(existing_emi_obligations=50_000)
        assert r2["foir"] > r1["foir"]


class TestProductNormalisation:
    def test_space_in_product_name(self):
        r = check_eligibility.invoke({
            "loan_product": "home loan",
            "monthly_income": 1_50_000, "loan_amount": 50_00_000,
            "tenure_months": 240, "age": 35, "employment_type": "salaried",
            "credit_score": 750,
        })
        assert "eligible" in r

    def test_unknown_product(self):
        r = check_eligibility.invoke({
            "loan_product": "crypto_loan",
            "monthly_income": 1_00_000, "loan_amount": 5_00_000,
            "tenure_months": 24, "age": 30, "employment_type": "salaried",
        })
        assert r["eligible"] is False
        assert "Unknown" in r["reason"]


class TestEscalationCeilings:
    @pytest.mark.parametrize("product,amount_above", [
        ("home_loan",     1_51_00_000),
        ("personal_loan", 41_00_000),
        ("msme_loan",     2_01_00_000),
        ("car_loan",      21_00_000),
    ])
    def test_escalation_triggers_above_ceiling(self, product, amount_above):
        r = check_eligibility.invoke({
            "loan_product": product,
            "monthly_income": 10_00_000,
            "loan_amount": amount_above,
            "tenure_months": 60,
            "age": 35,
            "employment_type": "salaried",
            "credit_score": 800,
        })
        assert r["escalate_to_rm"] is True
