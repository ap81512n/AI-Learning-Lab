
import asyncio
from collections.abc import Sequence
from typing import Protocol


class AsyncDocumentSource(Protocol):
    """Contract for fetching documents asynchronously."""

    async def fetch_document(self, document_id: int) -> str:
        """Fetch a document by its ID."""
        ...


class DocumentFetchService:
    """Coordinates document fetching through an async source."""

    def __init__(
        self,
        source: AsyncDocumentSource,
        max_concurrency: int = 5,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        self._source = source
        self._max_concurrency = max_concurrency

    async def fetch_sequential(
        self,
        document_ids: Sequence[int],
    ) -> list[str]:
        """Fetch documents one at a time."""

        results = []

        for document_id in document_ids:
            content = await self._source.fetch_document(
                document_id
            )
            results.append(content)

        return results

    async def fetch_concurrent(
        self,
        document_ids: Sequence[int],
    ) -> list[str]:
        """Fetch documents concurrently with a concurrency limit."""

        semaphore = asyncio.Semaphore(
            self._max_concurrency
        )

        async def fetch_one(document_id: int) -> str:
            async with semaphore:
                return await self._source.fetch_document(
                    document_id
                )

        results = await asyncio.gather(
            *(fetch_one(doc_id) for doc_id in document_ids)
        )

        return list(results)
