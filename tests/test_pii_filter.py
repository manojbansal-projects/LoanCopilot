"""Unit tests for safety/pii_filter.py"""
import pytest
from safety.pii_filter import mask, contains_pii


class TestAadhaarMasking:
    def test_spaced_aadhaar(self):
        assert "[AADHAAR REDACTED]" in mask("My Aadhaar is 1234 5678 9012")

    def test_hyphenated_aadhaar(self):
        assert "[AADHAAR REDACTED]" in mask("Aadhaar: 1234-5678-9012")

    def test_compact_aadhaar(self):
        assert "[AADHAAR REDACTED]" in mask("123456789012")

    def test_original_text_removed(self):
        result = mask("Aadhaar 1234 5678 9012 thanks")
        assert "1234" not in result


class TestPANMasking:
    def test_valid_pan(self):
        assert "[PAN REDACTED]" in mask("My PAN is ABCDE1234F")

    def test_pan_case_sensitive(self):
        # PAN must be uppercase — lowercase should not match
        result = mask("abcde1234f")
        assert "[PAN REDACTED]" not in result

    def test_pan_in_sentence(self):
        result = mask("Please share ABCDE1234F for verification")
        assert "ABCDE1234F" not in result


class TestMobileMasking:
    def test_10_digit_mobile(self):
        assert "[MOBILE REDACTED]" in mask("Call me at 9876543210")

    def test_plus91_prefix(self):
        assert "[MOBILE REDACTED]" in mask("+919876543210")

    def test_91_prefix(self):
        assert "[MOBILE REDACTED]" in mask("919876543210")

    def test_0_prefix(self):
        assert "[MOBILE REDACTED]" in mask("09876543210")

    def test_invalid_start_digit_not_masked(self):
        # Numbers starting with 1-5 are not valid Indian mobile numbers
        result = mask("1234567890")
        assert "[MOBILE REDACTED]" not in result


class TestEmailMasking:
    def test_simple_email(self):
        assert "[EMAIL REDACTED]" in mask("Email me at test@example.com")

    def test_email_with_dots(self):
        assert "[EMAIL REDACTED]" in mask("first.last@bank.co.in")

    def test_email_with_plus(self):
        assert "[EMAIL REDACTED]" in mask("user+tag@gmail.com")

    def test_email_removed_from_text(self):
        result = mask("Send to arjun@wipro.com please")
        assert "arjun@wipro.com" not in result


class TestAccountMasking:
    def test_9_digit_account(self):
        assert "[ACCOUNT REDACTED]" in mask("Account: 123456789")

    def test_16_digit_account(self):
        assert "[ACCOUNT REDACTED]" in mask("1234567890123456")


class TestMixedPII:
    def test_multiple_pii_types_in_one_string(self):
        text = "Name: Arjun, Mobile: 9876543210, Email: arjun@wipro.com, PAN: ABCDE1234F"
        result = mask(text)
        assert "[MOBILE REDACTED]" in result
        assert "[EMAIL REDACTED]" in result
        assert "[PAN REDACTED]" in result
        assert "9876543210" not in result
        assert "arjun@wipro.com" not in result
        assert "ABCDE1234F" not in result

    def test_clean_text_unchanged(self):
        text = "I want a home loan of 50 lakhs for 20 years."
        assert mask(text) == text


class TestFalsePositivePrevention:
    """Legitimate financial text that must NOT be masked."""

    def test_loan_amount_in_lakhs_not_masked(self):
        """'50 lakhs' is a loan amount, not PII — must pass through unchanged."""
        text = "I want a loan of 50 lakhs for 20 years"
        assert mask(text) == text

    def test_emi_amount_not_masked(self):
        text = "Your EMI will be approximately 45000 per month"
        result = mask(text)
        # 45000 (5 digits) is below the 9-digit account threshold
        assert "45000" in result

    def test_interest_rate_not_masked(self):
        text = "The interest rate is 8.75% per annum"
        assert mask(text) == text

    def test_short_numbers_not_account_masked(self):
        """Numbers < 9 digits should not be falsely masked as account numbers."""
        text = "FOIR is 45%"
        assert mask(text) == text

    def test_four_digit_pin_not_masked(self):
        text = "My PIN code is 4 digits"
        assert mask(text) == text

    def test_year_not_masked(self):
        text = "I need a loan for 2024 construction"
        # 2024 is 4 digits — well below account threshold
        assert mask(text) == text


class TestContainsPII:
    def test_detects_mobile(self):
        assert contains_pii("Call 9876543210") is True

    def test_detects_email(self):
        assert contains_pii("email: test@example.com") is True

    def test_detects_pan(self):
        assert contains_pii("PAN ABCDE1234F") is True

    def test_detects_aadhaar(self):
        assert contains_pii("Aadhaar 1234 5678 9012") is True

    def test_clean_text_returns_false(self):
        assert contains_pii("What documents do I need for a home loan?") is False
