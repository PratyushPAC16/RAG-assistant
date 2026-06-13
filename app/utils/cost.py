"""
Enterprise Agentic RAG Assistant
Cost & token-usage utilities — extracted here to break the circular
dependency between llm_factory and the agent modules that needed to
import these helpers.

Importing from this module instead of ``app.utils.llm_factory`` removes
the need for deferred (function-body) imports in router.py and synthesizer.py.
"""

from __future__ import annotations

from typing import Any

# ── Per-model pricing table (USD per 1 000 tokens) ───────────────────────────

_COST_TABLE: dict[str, tuple[float, float]] = {
    # (prompt_cost_per_1k, completion_cost_per_1k)
    "gemini-2.0-flash":        (0.000075, 0.000300),
    "gemini-1.5-flash":        (0.000075, 0.000300),
    "gemini-1.5-pro":          (0.001250, 0.005000),
    "llama-3.1-8b-instant":    (0.000059, 0.000079),
    "llama-3.3-70b-versatile": (0.000590, 0.000790),
    "llama3.2":                (0.000000, 0.000000),  # local — no API cost
}

_DEFAULT_PROMPT_COST     = 0.000075   # fallback prompt cost  ($/1k tokens)
_DEFAULT_COMPLETION_COST = 0.000300   # fallback completion cost ($/1k tokens)


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str | None = None,
) -> float:
    """
    Estimate the USD cost of one LLM call given token counts.

    Args:
        prompt_tokens:     Number of input/prompt tokens.
        completion_tokens: Number of generated/completion tokens.
        model_name:        Optional model name for per-model pricing.
                           Falls back to the default rate when not found.

    Returns:
        Estimated cost in USD (float).
    """
    if model_name and model_name in _COST_TABLE:
        prompt_rate, completion_rate = _COST_TABLE[model_name]
    else:
        prompt_rate     = _DEFAULT_PROMPT_COST
        completion_rate = _DEFAULT_COMPLETION_COST

    return (prompt_tokens * prompt_rate + completion_tokens * completion_rate) / 1_000


def extract_token_usage(response: Any) -> tuple[int, int, int]:
    """
    Extract (prompt_tokens, completion_tokens, total_tokens) from a
    LangChain LLM response object.

    Handles both ``response_metadata`` (LangChain ≥ 0.2) and legacy
    ``usage_metadata`` / ``token_usage`` dicts gracefully, returning
    ``(0, 0, 0)`` when usage information is unavailable.

    Args:
        response: A LangChain ``AIMessage`` or compatible response object.

    Returns:
        Tuple of (prompt_tokens, completion_tokens, total_tokens).
    """
    # LangChain ≥ 0.2 — preferred location
    meta = getattr(response, "response_metadata", {}) or {}
    usage = meta.get("usage_metadata") or meta.get("token_usage") or {}

    if not usage:
        # Fallback: some providers put it directly on the response
        usage = getattr(response, "usage_metadata", {}) or {}

    p_tok = int(usage.get("prompt_token_count") or usage.get("prompt_tokens") or 0)
    c_tok = int(
        usage.get("candidates_token_count")
        or usage.get("completion_tokens")
        or 0
    )
    t_tok = int(usage.get("total_token_count") or usage.get("total_tokens") or 0)

    # Compute total if missing
    if t_tok == 0 and (p_tok or c_tok):
        t_tok = p_tok + c_tok

    return p_tok, c_tok, t_tok
