import asyncio
import httpx
import time

BASE_URL = "http://localhost:8000"

async def make_request(client, index, query):
    payload = {
        "query": query,
        "use_web_search": False,
        "filter_document_ids": []
    }
    t0 = time.perf_counter()
    print(f"[Req {index}] Started query: '{query}' at {t0:.2f}s")
    try:
        resp = await client.post(f"{BASE_URL}/chat", json=payload, timeout=60.0)
        t1 = time.perf_counter()
        dur = t1 - t0
        print(f"[Req {index}] Finished at {t1:.2f}s (duration: {dur:.2f}s, status: {resp.status_code})")
        return dur
    except Exception as e:
        t1 = time.perf_counter()
        print(f"[Req {index}] Failed at {t1:.2f}s with error: {e}")
        return t1 - t0

async def main():
    async with httpx.AsyncClient() as client:
        # We query questions that require LLM synthesis to ensure they take non-trivial time
        queries = [
            "Explain what neural networks are in 3 simple sentences.",
            "Compare search engine indexing with vector database chunking in 3 simple sentences."
        ]
        
        t_start = time.perf_counter()
        durations = await asyncio.gather(
            make_request(client, 1, queries[0]),
            make_request(client, 2, queries[1])
        )
        t_end = time.perf_counter()
        total_time = t_end - t_start
        print(f"\nSummary:")
        print(f"  Request 1 duration: {durations[0]:.2f}s")
        print(f"  Request 2 duration: {durations[1]:.2f}s")
        print(f"  Total wall clock time: {total_time:.2f}s")
        
        # In a fully sequential/blocking scenario, wall clock time would be at least sum(durations).
        # In a parallel scenario, wall clock time should be close to max(durations) + small overhead.
        overlap = sum(durations) - total_time
        if overlap > 0.5:
            print(f"  SUCCESS: Requests ran concurrently! Overlap: {overlap:.2f}s")
        else:
            print("  WARNING: Requests appeared to run sequentially (no overlapping). Ensure the server is running.")

if __name__ == "__main__":
    asyncio.run(main())
