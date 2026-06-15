"""Unit tests for deployment/config.py — constants and environment defaults.

These tests verify that all product-level constants are internally consistent
and that the configuration module loads without error.
"""
from __future__ import annotations

import pytest
from deployment.config import (
    ESCALATION_CEILINGS,
    RAG_TOP_K,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    MEMORY_WINDOW,
    MAX_ITERATIONS,
    SAFETY_SCORE_THRESHOLD,
    CHROMA_COLLECTION_NAME,
    ROOT_DIR,
    KNOWLEDGE_BASE_PATH,
    CHROMA_DB_PATH,
)
from tools.eligibility_checker import PRODUCT_LIMITS, RATE_BANDS


PRODUCTS = ["home_loan", "personal_loan", "msme_loan", "car_loan"]


class TestEscalationCeilings:
    def test_all_four_products_present(self):
        assert set(ESCALATION_CEILINGS.keys()) == set(PRODUCTS)

    @pytest.mark.parametrize("product", PRODUCTS)
    def test_ceiling_is_positive_integer(self, product):
        v = ESCALATION_CEILINGS[product]
        assert isinstance(v, int), f"{product} ceiling must be int, got {type(v)}"
        assert v > 0

    def test_home_loan_ceiling_is_1_5_cr(self):
        assert ESCALATION_CEILINGS["home_loan"] == 1_50_00_000

    def test_personal_loan_ceiling_equals_product_max(self):
        # Personal loan ceiling == product max (₹40L)
        assert ESCALATION_CEILINGS["personal_loan"] == PRODUCT_LIMITS["personal_loan"]["max"]

    def test_car_loan_ceiling_equals_product_max(self):
        # Car loan ceiling == product max (₹20L)
        assert ESCALATION_CEILINGS["car_loan"] == PRODUCT_LIMITS["car_loan"]["max"]

    def test_msme_loan_ceiling_below_product_max(self):
        # MSME ceiling (₹2Cr) < product max (₹10Cr) — room for RM to handle large loans
        assert ESCALATION_CEILINGS["msme_loan"] < PRODUCT_LIMITS["msme_loan"]["max"]

    @pytest.mark.parametrize("product", PRODUCTS)
    def test_ceiling_does_not_exceed_product_max(self, product):
        assert ESCALATION_CEILINGS[product] <= PRODUCT_LIMITS[product]["max"]


class TestProductLimits:
    def test_all_four_products_present(self):
        assert set(PRODUCT_LIMITS.keys()) == set(PRODUCTS)

    @pytest.mark.parametrize("product", PRODUCTS)
    def test_min_less_than_max(self, product):
        assert PRODUCT_LIMITS[product]["min"] < PRODUCT_LIMITS[product]["max"]

    @pytest.mark.parametrize("product", PRODUCTS)
    def test_max_tenure_positive(self, product):
        assert PRODUCT_LIMITS[product]["max_tenure"] > 0

    def test_home_loan_max_tenure_360(self):
        assert PRODUCT_LIMITS["home_loan"]["max_tenure"] == 360  # 30 years

    def test_personal_loan_max_tenure_60(self):
        assert PRODUCT_LIMITS["personal_loan"]["max_tenure"] == 60  # 5 years

    def test_car_loan_max_tenure_84(self):
        assert PRODUCT_LIMITS["car_loan"]["max_tenure"] == 84   # 7 years


class TestRateBands:
    def test_all_four_products_present(self):
        assert set(RATE_BANDS.keys()) == set(PRODUCTS)

    @pytest.mark.parametrize("product", PRODUCTS)
    def test_low_rate_less_than_high_rate(self, product):
        lo, hi = RATE_BANDS[product]
        assert lo < hi, f"{product}: low rate {lo} must be < high rate {hi}"

    @pytest.mark.parametrize("product", PRODUCTS)
    def test_rates_are_realistic(self, product):
        lo, hi = RATE_BANDS[product]
        # Sanity: rates should be between 5% and 30% for Indian retail loans
        assert 5.0 <= lo <= 30.0
        assert 5.0 <= hi <= 30.0


class TestRAGConstants:
    def test_top_k_positive(self):
        assert RAG_TOP_K > 0

    def test_chunk_size_positive(self):
        assert RAG_CHUNK_SIZE > 0

    def test_chunk_overlap_less_than_size(self):
        assert RAG_CHUNK_OVERLAP < RAG_CHUNK_SIZE

    def test_collection_name_is_string(self):
        assert isinstance(CHROMA_COLLECTION_NAME, str)
        assert len(CHROMA_COLLECTION_NAME) > 0


class TestAgentConstants:
    def test_memory_window_positive(self):
        assert MEMORY_WINDOW > 0

    def test_max_iterations_positive(self):
        assert MAX_ITERATIONS > 0

    def test_safety_score_threshold_between_0_and_1(self):
        assert 0.0 < SAFETY_SCORE_THRESHOLD <= 1.0


class TestPaths:
    def test_root_dir_exists(self):
        assert ROOT_DIR.exists()

    def test_knowledge_base_path_is_path_object(self):
        import pathlib
        assert isinstance(KNOWLEDGE_BASE_PATH, pathlib.Path)

    def test_chroma_db_path_is_path_object(self):
        import pathlib
        assert isinstance(CHROMA_DB_PATH, pathlib.Path)
