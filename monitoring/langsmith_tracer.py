"""
PLACEHOLDER — LangSmith is NOT used in this project.

Architectural decision: LangSmith is a cloud-only service. Banking regulations
and PII handling requirements (Aadhaar, PAN, income data) preclude sending
conversation traces to a third-party cloud provider.

The project uses Langfuse self-hosted for all observability, tracing, and
evaluation. See monitoring/langfuse_logger.py and docs/engineering_justification.md.
"""
raise ImportError(
    "LangSmith is excluded from this project. Use monitoring.langfuse_logger instead."
)
