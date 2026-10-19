"""Ingestion service built by composition over a DocumentLoader.

All Pydantic models come from models.py; this module only holds behavior.
"""

from __future__ import annotations
from pathlib import Path
from typing import ClassVar, Iterable
from fde_learning_lab.exceptions import DocumentError
from fde_learning_lab.loaders import DocumentLoader
from fde_learning_lab.models import IngestedDocument, IngestionFailure, IngestionResult
from collections.abc import Iterator
from pathlib import Path
from fde_learning_lab.loaders import StreamingDocumentLoader


class StreamingIngestionService:
    def __init__(self, loader: StreamingDocumentLoader):
        self.loader = loader

    def iter_ingest(self, file_path: str | Path) -> Iterator[str]:
        path = Path(file_path)

        for line in self.loader.iter_lines(path):
            cleaned = line.strip()

            if cleaned:
                yield cleaned


class IngestionService:
    """Ingests documents using whatever loader it is given.

    The service depends only on the DocumentLoader protocol. It never
    inspects the concrete type: any object with a matching `load()` works.
    """

    def __init__(self, loader: DocumentLoader) -> None:
        self._loader = loader  # has-a loader (composition), not is-a loader

    def ingest(self, path: str | Path) -> IngestedDocument:
        """Load a single document. DocumentError subclasses propagate."""
        p = Path(path)
        content = self._loader.load(p)  # duck-typed call, no isinstance checks
        return IngestedDocument(path=p, content=content)

    def ingest_many(self, paths: Iterable[str | Path]) -> IngestionResult:
        """Load many documents; collect failures instead of stopping on the first."""
        result = IngestionResult()
        for path in paths:
            p = Path(path)
            try:
                result.documents.append(self.ingest(p))
            except DocumentError as exc:
                result.failures.append(IngestionFailure.from_exception(p, exc))
        return result


if __name__ == "__main__":
    from fde_learning_lab.loaders import TextLoader

    paths = ["notes.txt", "missing.txt", "report.pdf"]

    # Same service class, same calling code -- only the injected loader differs.
    for loader in (TextLoader(), MockLoader("hello from the mock")):
        service = IngestionService(loader)
        outcome = service.ingest_many(paths)

        print(f"\n=== {type(loader).__name__} ===")
        for doc in outcome.documents:
            print(f"OK   {doc.path} ({doc.char_count} chars)")
        for f in outcome.failures:
            print(f"FAIL {f.path}: {f.error_type}: {f.message}")

        payload = outcome.model_dump_json()
        assert IngestionResult.model_validate_json(payload) == outcome  # round-trip