"""Run Langfuse dataset evaluations against all three test sets."""
from __future__ import annotations
import json
from pathlib import Path
from langfuse import Langfuse
from deployment.config import DATA_DIR, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST


def load_test_cases(filename: str) -> list[dict]:
    path = DATA_DIR / "evaluation" / filename
    return json.loads(path.read_text(encoding="utf-8"))


def run_rag_eval(agent_fn, dataset_name: str = "rag_20q") -> dict:
    """Run the 20-question RAG evaluation set; return pass/fail summary."""
    # TODO (Phase 9): implement Langfuse dataset run and LLM-as-judge scoring
    raise NotImplementedError


def run_tool_eval(agent_fn, dataset_name: str = "tool_30scenarios") -> dict:
    """Run 30 tool-selection scenarios; return per-tool accuracy."""
    raise NotImplementedError


def run_safety_eval(agent_fn, dataset_name: str = "safety_5prompts") -> dict:
    """Run 5 adversarial safety prompts; return block rate."""
    raise NotImplementedError
