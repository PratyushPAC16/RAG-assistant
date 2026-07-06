from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import BenchmarkProviderResult, BenchmarkRun
from app.rag.retriever import get_retriever
from app.utils.config import get_settings
from app.api.dependencies import _require_api_key
from app.api.state import (
    BENCHMARK_FILE,
    _benchmark_runs,
    _load_benchmark_history,
    _persist_benchmark_run,
)

router = APIRouter(tags=["Benchmark"])
settings = get_settings()
logger = logging.getLogger(__name__)

_BENCHMARK_PROMPT_TEMPLATE = """You are an expert AI assistant. Answer the following question clearly and concisely.

{context_block}QUESTION:
{query}

ANSWER:"""

_FAITHFULNESS_PROMPT = """
You are an evaluator measuring the faithfulness and relevance of an AI response against the provided reference context.

Context:
{context}

AI Response:
{response}

Evaluate the response faithfulness on a scale of 0 to 100 where:
- 100 = fully faithful, every claim grounded in the context
- 0 = completely unfaithful, fabricated or unrelated

Respond with ONLY a JSON object:
{{"score": <integer 0-100>, "reasoning": "<one sentence explanation>"}}"""


@router.post(
    "/benchmark",
    summary="Run a prompt across all LLM providers and compare results",
)
async def run_benchmark(
    query: str,
    use_rag: bool = False,
    temperature: float = 0.1,
) -> dict:
    """
    Execute a prompt concurrently across Ollama, Groq, and Gemini.
    Measures latency, token usage, cost, response length, and retrieval accuracy.
    """
    from app.utils.llm_factory import get_provider_llm, extract_token_usage, calculate_provider_cost

    # ── 1. Optional: retrieve RAG context ─────────────────────────────────────
    context_text = ""
    context_block = ""
    if use_rag:
        try:
            retriever = get_retriever()
            chunks = retriever.retrieve(query=query, top_k=5)
            if chunks:
                parts = []
                for i, c in enumerate(chunks, 1):
                    parts.append(f"[{i}] {c.metadata.source}: {c.content[:600]}")
                context_text = "\n".join(parts)
                context_block = f"CONTEXT FROM DOCUMENTS:\n{context_text}\n\n"
        except Exception as exc:
            logger.warning(f"RAG retrieval failed during benchmark: {exc}")

    prompt_text = _BENCHMARK_PROMPT_TEMPLATE.format(
        context_block=context_block, query=query
    )

    # ── 2. Provider configs ────────────────────────────────────────────────────
    provider_configs = [
        ("gemini",  settings.gemini_model),
        ("groq",    settings.groq_model),
        ("ollama",  settings.ollama_model),
    ]

    # ── 3. Concurrent invocation via asyncio ──────────────────────────────────
    async def call_provider(provider: str, model: str) -> BenchmarkProviderResult:
        loop = asyncio.get_running_loop()
        try:
            llm = await loop.run_in_executor(
                None, lambda: get_provider_llm(provider, temperature=temperature)
            )
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content="You are a helpful AI assistant."),
                HumanMessage(content=prompt_text),
            ]
            t0 = time.perf_counter()
            response = await loop.run_in_executor(None, lambda: llm.invoke(messages))
            latency_s = time.perf_counter() - t0

            content = response.content or ""
            p_tok, c_tok, t_tok = extract_token_usage(response)
            # Fallback estimate when provider returns no token counts
            if t_tok == 0:
                estimated = max(1, int((len(prompt_text) + len(content)) / 4))
                p_tok = int(len(prompt_text) / 4)
                c_tok = estimated - p_tok
                t_tok = estimated

            cost = calculate_provider_cost(provider, p_tok, c_tok)
            words = len(content.split())

            return BenchmarkProviderResult(
                provider=provider,
                model=model,
                response=content,
                latency_s=round(latency_s, 3),
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=t_tok,
                cost_usd=round(cost, 8),
                response_length_chars=len(content),
                response_length_words=words,
            )
        except Exception as exc:
            return BenchmarkProviderResult(
                provider=provider,
                model=model,
                response="",
                latency_s=0.0,
                error=str(exc),
            )

    tasks = [call_provider(p, m) for p, m in provider_configs]
    raw_results: list[BenchmarkProviderResult] = await asyncio.gather(*tasks)
    results_map: dict[str, BenchmarkProviderResult] = {r.provider: r for r in raw_results}

    # ── 4. Retrieval Accuracy via LLM faithfulness evaluator ──────────────────
    eval_context = context_text if use_rag and context_text else query

    async def evaluate_faithfulness(res: BenchmarkProviderResult) -> None:
        if res.error or not res.response:
            res.retrieval_accuracy = 0.0
            res.evaluation_reasoning = "Provider returned an error — faithfulness N/A."
            return
        loop = asyncio.get_running_loop()
        try:
            from langchain_core.messages import HumanMessage
            eval_llm = await loop.run_in_executor(
                None, lambda: get_provider_llm(settings.llm_provider.lower(), temperature=0.0)
            )
            eval_prompt = _FAITHFULNESS_PROMPT.format(
                context=eval_context[:3000], response=res.response[:2000]
            )
            eval_resp = await loop.run_in_executor(
                None, lambda: eval_llm.invoke([HumanMessage(content=eval_prompt)])
            )
            raw = eval_resp.content.strip()
            # Extract JSON from possible code-fence wrapping
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            if m:
                data = json.loads(m.group())
                res.retrieval_accuracy = float(data.get("score", 80.0))
                res.evaluation_reasoning = data.get("reasoning", "")
            else:
                res.retrieval_accuracy = 80.0
                res.evaluation_reasoning = "Could not parse evaluator output."
        except Exception as exc:
            logger.warning(f"Faithfulness eval failed for {res.provider}: {exc}")
            res.retrieval_accuracy = 75.0
            res.evaluation_reasoning = f"Evaluation error: {exc}"

    await asyncio.gather(*[evaluate_faithfulness(r) for r in raw_results])

    # ── 5. Composite score ────────────────────────────────────────────────────
    active = [r for r in raw_results if not r.error]
    if active:
        max_lat = max(r.latency_s for r in active) or 1.0
        max_cost = max(r.cost_usd for r in active) or 1e-9
        for r in active:
            speed_score    = max(0, (1 - r.latency_s / max_lat)) * 100
            cost_score     = max(0, (1 - r.cost_usd  / max_cost)) * 100
            r.composite_score = round(
                0.5 * r.retrieval_accuracy + 0.3 * speed_score + 0.2 * cost_score, 2
            )

    # ── 6. Persist and return ─────────────────────────────────────────────────
    run = BenchmarkRun(
        query=query,
        context_retrieved=context_text,
        use_rag=use_rag,
        results=results_map,
    )
    _benchmark_runs.append(run)
    _persist_benchmark_run(run)

    return run.model_dump(mode="json")


@router.get(
    "/benchmark/history",
    summary="Retrieve all stored benchmark run history",
)
async def get_benchmark_history(limit: int = 50) -> dict:
    """
    Return the most recent benchmark runs from the persistent JSONL store.
    """
    history = _load_benchmark_history()
    return {
        "total": len(history),
        "runs": [r.model_dump(mode="json") for r in history[-limit:]],
    }


@router.delete(
    "/benchmark/history",
    summary="Clear all stored benchmark history",
    dependencies=[Depends(_require_api_key)],
)
async def clear_benchmark_history() -> dict:
    """
    Delete the benchmark_runs.jsonl file and reset the in-memory store.
    """
    global _benchmark_runs
    # Wait, we need to clear the _benchmark_runs list imported from state.py.
    # Since list is mutable, clearing it in-place is the best option to keep other modules referenced to it updated!
    _benchmark_runs.clear()
    try:
        if BENCHMARK_FILE.exists():
            BENCHMARK_FILE.unlink()
        return {"status": "cleared", "message": "Benchmark history cleared successfully."}
    except Exception as exc:
        logger.error("Failed to clear benchmark history", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear benchmark history. Check server logs for details.",
        )
