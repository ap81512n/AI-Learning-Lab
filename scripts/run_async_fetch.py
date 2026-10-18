
import asyncio
import time

from fde_learning_lab.async_fetch import DocumentFetchService


class SimulatedRemoteDocumentSource:
    """Simulates remote document retrieval with network latency."""

    def __init__(self, delay_seconds: float = 0.3) -> None:
        self.delay_seconds = delay_seconds

    async def fetch_document(self, document_id: int) -> str:
        print(f"Fetching document {document_id}")

        # Simulate waiting for a remote service.
        await asyncio.sleep(self.delay_seconds)
        # time.sleep(self.delay_seconds)

        print(f"Completed document {document_id}")

        return f"Document {document_id}: Example content"


async def main() -> None:
    document_ids = [1, 2, 3, 4, 5]

    source = SimulatedRemoteDocumentSource()

    service = DocumentFetchService(
        source=source,
        max_concurrency=5,
    )

    print("\n--- SEQUENTIAL FETCH ---")

    start = time.perf_counter()

    sequential_results = await service.fetch_sequential(
        document_ids
    )

    sequential_duration = time.perf_counter() - start

    print("\n--- CONCURRENT FETCH ---")

    start = time.perf_counter()

    concurrent_results = await service.fetch_concurrent(
        document_ids
    )

    concurrent_duration = time.perf_counter() - start

    assert sequential_results == concurrent_results

    print("\n--- RESULTS ---")

    print(f"Sequential: {sequential_duration:.2f} seconds")
    print(f"Concurrent: {concurrent_duration:.2f} seconds")

    if concurrent_duration > 0:
        speedup = sequential_duration / concurrent_duration
        print(f"Speedup: {speedup:.2f}x")

    print(f"Documents fetched: {len(concurrent_results)}")


if __name__ == "__main__":
    asyncio.run(main())
