"""Unit tests for tools/document_checklist.py"""
import pytest
from tools.document_checklist import get_document_checklist, _COMMON_DOCS


def _get(product, emp):
    return get_document_checklist.invoke({"loan_product": product,
                                          "employment_type": emp})


class TestCommonDocs:
    def test_common_docs_always_present(self):
        r = _get("home_loan", "salaried")
        for doc in _COMMON_DOCS:
            assert doc in r["common_docs"]

    def test_note_present(self):
        r = _get("home_loan", "salaried")
        assert "indicative" in r["note"].lower()


class TestProductEmploymentCombinations:
    def test_home_loan_salaried(self):
        r = _get("home_loan", "salaried")
        docs = r["product_specific_docs"]
        assert any("salary slip" in d.lower() for d in docs)
        assert any("form 16" in d.lower() for d in docs)
        assert any("property" in d.lower() for d in docs)

    def test_home_loan_self_employed(self):
        r = _get("home_loan", "self_employed")
        docs = r["product_specific_docs"]
        assert any("it return" in d.lower() for d in docs)
        assert any("p&l" in d.lower() or "profit" in d.lower() for d in docs)

    def test_personal_loan_salaried(self):
        r = _get("personal_loan", "salaried")
        docs = r["product_specific_docs"]
        assert any("salary slip" in d.lower() for d in docs)
        assert any("employment" in d.lower() for d in docs)

    def test_personal_loan_self_employed(self):
        r = _get("personal_loan", "self_employed")
        docs = r["product_specific_docs"]
        assert any("it return" in d.lower() for d in docs)

    def test_msme_loan_business(self):
        r = _get("msme_loan", "business")
        docs = r["product_specific_docs"]
        assert any("gst" in d.lower() for d in docs)
        assert any("business registration" in d.lower() or "registration" in d.lower() for d in docs)

    def test_car_loan_salaried(self):
        r = _get("car_loan", "salaried")
        docs = r["product_specific_docs"]
        assert any("proforma" in d.lower() or "invoice" in d.lower() for d in docs)
        assert any("salary slip" in d.lower() for d in docs)

    def test_car_loan_self_employed(self):
        r = _get("car_loan", "self_employed")
        docs = r["product_specific_docs"]
        assert any("it return" in d.lower() for d in docs)
        assert any("proforma" in d.lower() or "invoice" in d.lower() for d in docs)


    # ── Fallback combinations (not in _BY_PRODUCT_EMPLOYMENT) ────────────────

    def test_home_loan_business_falls_back(self):
        """home_loan + business has no specific mapping → branch fallback."""
        r = _get("home_loan", "business")
        assert len(r["product_specific_docs"]) == 1
        assert "branch" in r["product_specific_docs"][0].lower()

    def test_personal_loan_business_falls_back(self):
        r = _get("personal_loan", "business")
        assert "branch" in r["product_specific_docs"][0].lower()

    def test_msme_loan_salaried_falls_back(self):
        """msme_loan is designed for business owners; salaried → fallback."""
        r = _get("msme_loan", "salaried")
        assert "branch" in r["product_specific_docs"][0].lower()

    def test_msme_loan_self_employed_falls_back(self):
        r = _get("msme_loan", "self_employed")
        assert "branch" in r["product_specific_docs"][0].lower()

    def test_car_loan_business_falls_back(self):
        r = _get("car_loan", "business")
        assert "branch" in r["product_specific_docs"][0].lower()

    # ── Output keys always present ────────────────────────────────────────────

    def test_output_contains_all_keys(self):
        r = _get("home_loan", "salaried")
        for key in ("loan_product", "employment_type", "common_docs", "product_specific_docs", "note"):
            assert key in r, f"Key '{key}' missing from output"

    def test_common_docs_is_list(self):
        r = _get("car_loan", "self_employed")
        assert isinstance(r["common_docs"], list)

    def test_product_specific_docs_is_list(self):
        r = _get("msme_loan", "business")
        assert isinstance(r["product_specific_docs"], list)


class TestUnknownCombination:
    def test_unknown_falls_back_to_branch(self):
        r = _get("home_loan", "freelancer")
        assert len(r["product_specific_docs"]) == 1
        assert "branch" in r["product_specific_docs"][0].lower()

    def test_unknown_product(self):
        r = _get("boat_loan", "salaried")
        assert "branch" in r["product_specific_docs"][0].lower()


class TestInputNormalisation:
    def test_spaces_in_product_name(self):
        r = _get("home loan", "salaried")
        assert len(r["product_specific_docs"]) > 1

    def test_business_owner_alias(self):
        r_canonical = _get("msme_loan", "business")
        r_alias     = _get("msme_loan", "business_owner")
        assert r_canonical["product_specific_docs"] == r_alias["product_specific_docs"]

    def test_product_and_employment_in_output(self):
        r = _get("car_loan", "salaried")
        assert r["loan_product"] == "car_loan"
        assert r["employment_type"] == "salaried"
