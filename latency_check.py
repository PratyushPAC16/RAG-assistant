"""
Quick latency benchmark — sends 3 representative queries to the running
FastAPI backend and prints per-stage timing breakdowns.
Run with: python latency_check.py
"""
import urllib.request
import json
import time

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

test_cases = [
    (
        "RAG query (clear doc keyword → fast-path expected)",
        {"query": "What does the document say about the main topics?", "session_id": "lt_rag"},
    ),
    (
        "WEB query (clear web keyword → fast-path expected)",
        {"query": "What are the latest AI trends in 2026?", "session_id": "lt_web"},
    ),
    (
        "AMBIGUOUS query (no clear keyword → LLM routing expected)",
        {"query": "Explain neural networks to me", "session_id": "lt_amb"},
    ),
]

for label, payload in test_cases:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + "/chat", data=data, headers=HEADERS, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read())
        wall = (time.perf_counter() - t0) * 1000

        lms   = body.get("latency_ms", {})
        trace = body.get("routing_trace", [])
        agent = body.get("agent_used", "?")

        routing_ms = lms.get("routing")
        routing_label = (
            "FAST-PATH — 0 ms (no LLM call)"
            if routing_ms is None
            else f"{routing_ms:.0f} ms  ← LLM was invoked"
        )

        print(f"\n{'='*65}")
        print(f"  {label}")
        print(f"{'='*65}")
        print(f"  Agent used  : {agent}")
        print(f"  Routing     : {routing_label}")
        print(f"  Retrieval   : {lms.get('retrieval', 'n/a')} ms")
        print(f"  Reranking   : {lms.get('reranking', 'n/a')} ms")
        print(f"  Web search  : {lms.get('web_search', 'n/a')} ms")
        print(f"  Synthesis   : {lms.get('synthesis_llm', 'n/a')} ms")
        print(f"  Pipeline total: {lms.get('total', 'n/a')} ms")
        print(f"  Wall clock  : {wall:.0f} ms")
        print(f"  Routing trace:")
        for t in trace:
            print(f"    → {t}")

    except Exception as e:
        wall = (time.perf_counter() - t0) * 1000
        print(f"\n  [{label}]")
        print(f"  ERROR after {wall:.0f} ms: {e}")

print("\nDone.")
