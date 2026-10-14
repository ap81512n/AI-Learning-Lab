"""Document loader protocol and a UTF-8 text loader."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from fde_learning_lab.exceptions import (
    DocumentNotFoundError,
    DocumentReadError,
    UnsupportedDocumentError,
)


@runtime_checkable
class DocumentLoader(Protocol):
    """Anything that can load a document from a path into text.

    Structural typing: a class doesn't need to inherit from this,
    it just needs `supported_extensions`, `supports()` and `load()`.
    """

    supported_extensions: ClassVar[tuple[str, ...]]

    def supports(self, path: str | Path) -> bool:
        """Return True if this loader can handle the given path."""
        ...

    def load(self, path: str | Path) -> str:
        """Load the document and return its contents as text.

        Raises:
            DocumentNotFoundError: path does not exist or is not a file.
            UnsupportedDocumentError: extension not handled by this loader.
            DocumentReadError: file exists but cannot be read/decoded.
        """
        ...


class TextLoader:
    """Loads plain-text documents encoded as UTF-8."""

    supported_extensions: ClassVar[tuple[str, ...]] = (".txt", ".md", ".log", ".csv")

    def __init__(self, encoding: str = "utf-8", strip_bom: bool = True) -> None:
        self.encoding = encoding
        # "utf-8-sig" transparently drops a leading BOM if present
        self._read_encoding = "utf-8-sig" if strip_bom and encoding == "utf-8" else encoding

    def supports(self, path: str | Path) -> bool:
        return Path(path).suffix.lower() in self.supported_extensions

    def load(self, path: str | Path) -> str:
        p = Path(path)

        if not p.is_file():
            raise DocumentNotFoundError(p)
        if not self.supports(p):
            raise UnsupportedDocumentError(p, self.supported_extensions)

        try:
            return p.read_text(encoding=self._read_encoding)
        except UnicodeDecodeError as exc:
            raise DocumentReadError(
                p, f"Not valid {self.encoding} at byte {exc.start}: {exc.reason}"
            ) from exc
        except OSError as exc:  # permissions, is-a-directory races, I/O errors
            raise DocumentReadError(p, f"Failed to read document: {exc}") from exc


class MockLoader:
    """Second DocumentLoader implementation: returns fixed content, never touches disk.

    It does not inherit from DocumentLoader or TextLoader. It satisfies the
    protocol structurally by having the same members, so IngestionService
    accepts it unchanged.
    """

    supported_extensions: ClassVar[tuple[str, ...]] = ()  # accepts any path

    def __init__(self, content: str = "mock document content") -> None:
        self.content = content
        self.calls: list[Path] = []  # records which paths were requested

    def supports(self, path: str | Path) -> bool:
        return True

    def load(self, path: str | Path) -> str:
        self.calls.append(Path(path))
        return self.content


if __name__ == "__main__":
    loaders: list[DocumentLoader] = [   # type checker verifies each conforms
        TextLoader(),
        MockLoader("fixed content"),
    ]

    for loader in loaders:
        # True for both, thanks to @runtime_checkable
        print(f"{type(loader).__name__}: {isinstance(loader, DocumentLoader)}")

    mock = MockLoader("fixed content")
    print(mock.load("any/path.pdf"))   # -> fixed content (no file needed)
    print(mock.calls)                  # -> [PosixPath('any/path.pdf')]