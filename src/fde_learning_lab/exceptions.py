"""Custom exception hierarchy for document handling.

DocumentError                  (base for all document problems)
├── DocumentNotFoundError      (also a FileNotFoundError)
├── DocumentReadError          (exists but couldn't be read/parsed)
└── UnsupportedDocumentError   (format/extension not supported)
"""

from __future__ import annotations

from pathlib import Path


class DocumentError(Exception):
    """Base class for all document-related errors."""

    def __init__(self, message: str, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.message} (path={self.path})" if self.path else self.message


class DocumentNotFoundError(DocumentError, FileNotFoundError):
    """Raised when a document does not exist at the given path."""

    def __init__(self, path: str | Path) -> None:
        super().__init__("Document not found", path)


class DocumentReadError(DocumentError):
    """Raised when a document exists but cannot be read or parsed."""

    def __init__(self, path: str | Path, reason: str = "Unable to read document") -> None:
        super().__init__(reason, path)


class UnsupportedDocumentError(DocumentError):
    """Raised when a document's type/extension is not supported."""

    def __init__(
        self,
        path: str | Path,
        supported: tuple[str, ...] = (),
    ) -> None:
        self.extension = Path(path).suffix.lower() or "<none>"
        self.supported = supported
        msg = f"Unsupported document type '{self.extension}'"
        if supported:
            msg += f"; supported: {', '.join(supported)}"
        super().__init__(msg, path)


# --------------------------------------------------------------------------- #
# Example usage
# --------------------------------------------------------------------------- #
SUPPORTED = (".txt", ".md", ".json")


def load_document(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise DocumentNotFoundError(p)
    if p.suffix.lower() not in SUPPORTED:
        raise UnsupportedDocumentError(p, SUPPORTED)
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # Chain the original exception so the root cause stays in the traceback
        raise DocumentReadError(p, f"Failed to read document: {exc}") from exc


if __name__ == "__main__":
    for candidate in ("missing.txt", "report.pdf"):
        try:
            load_document(candidate)
        except UnsupportedDocumentError as e:
            print("Unsupported:", e)
        except DocumentNotFoundError as e:
            print("Not found:", e)
        except DocumentError as e:  # catch-all for anything else in the family
            print("Document error:", e)