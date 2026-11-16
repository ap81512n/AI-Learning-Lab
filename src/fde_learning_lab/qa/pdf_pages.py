"""Extract page-numbered text from saved PDF uploads."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


@dataclass(frozen=True)
class DocumentPage:
    page_number: int
    text: str


class PdfExtractionError(Exception):
    """The stored PDF could not be parsed."""


def extract_pdf_pages(pdf_path: Path) -> list[DocumentPage]:
    """Return 1-based page numbers with their extracted text."""
    try:
        reader = PdfReader(pdf_path)
        return [
            DocumentPage(
                page_number=index,
                text=page.extract_text() or "",
            )
            for index, page in enumerate(reader.pages, start=1)
        ]
    except (PyPdfError, OSError, ValueError) as exc:
        raise PdfExtractionError(
            "Stored PDF could not be read"
        ) from exc
