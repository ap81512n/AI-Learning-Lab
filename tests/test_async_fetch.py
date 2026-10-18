
import asyncio

import pytest

from fde_learning_lab.async_fetch import DocumentFetchService


class TrackingDocumentSource:
    """Fake source that tracks active requests."""

    def __init__(self, delay_seconds: float = 0.01) -> None:
        self.delay_seconds = delay_seconds
        self.active_requests = 0
        self.max_active_requests = 0

    async def fetch_document(self, document_id: int) -> str:
        self.active_requests += 1

        self.max_active_requests = max(
            self.max_active_requests,
            self.active_requests,
        )

        try:
            await asyncio.sleep(self.delay_seconds)
            return f"Document {document_id}"
        finally:
            self.active_requests -= 1


def test_sequential_fetch_returns_documents() -> None:
    source = TrackingDocumentSource()
    service = DocumentFetchService(source)

    results = asyncio.run(
        service.fetch_sequential([1, 2, 3])
    )

    assert results == [
        "Document 1",
        "Document 2",
        "Document 3",
    ]
    assert source.max_active_requests == 1


def test_concurrent_fetch_returns_documents() -> None:
    source = TrackingDocumentSource()
    service = DocumentFetchService(source)

    results = asyncio.run(
        service.fetch_concurrent([1, 2, 3])
    )

    assert results == [
        "Document 1",
        "Document 2",
        "Document 3",
    ]

    assert source.max_active_requests == 3


def test_concurrency_limit() -> None:
    source = TrackingDocumentSource()

    service = DocumentFetchService(
        source,
        max_concurrency=2,
    )

    results = asyncio.run(
        service.fetch_concurrent([1, 2, 3, 4, 5])
    )

    assert len(results) == 5
    assert source.max_active_requests == 2


def test_invalid_concurrency_limit() -> None:
    source = TrackingDocumentSource()

    with pytest.raises(ValueError):
        DocumentFetchService(
            source,
            max_concurrency=0,
        )


def test_results_preserve_input_order() -> None:
    class OutOfOrderSource:
        async def fetch_document(
            self, document_id: int
        ) -> str:
            await asyncio.sleep(
                (4 - document_id) * 0.01
            )
            return f"Document {document_id}"

    service = DocumentFetchService(OutOfOrderSource())

    results = asyncio.run(
        service.fetch_concurrent([1, 2, 3])
    )

    assert results == [
        "Document 1",
        "Document 2",
        "Document 3",
    ]


def test_fetch_failure_propagates() -> None:
    class FailingSource:
        async def fetch_document(
            self, document_id: int
        ) -> str:
            raise RuntimeError("Remote service unavailable")

    service = DocumentFetchService(FailingSource())

    with pytest.raises(
        RuntimeError,
        match="Remote service unavailable",
    ):
        asyncio.run(service.fetch_concurrent([1]))
