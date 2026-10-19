import pytest

from fde_learning_lab.exceptions import DocumentNotFoundError
from fde_learning_lab.ingestion import StreamingIngestionService
from fde_learning_lab.loaders import StreamingTextLoader


def test_streams_document(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text(
        "  First line  \n\nSecond line\n",
        encoding="utf-8",
    )

    service = StreamingIngestionService(
        StreamingTextLoader()
    )

    result = list(service.iter_ingest(path))

    assert result == ["First line", "Second line"]


def test_missing_document(tmp_path):
    service = StreamingIngestionService(
        StreamingTextLoader()
    )

    with pytest.raises(DocumentNotFoundError):
        list(service.iter_ingest(tmp_path / "missing.txt"))


def test_lazy_execution():
    class SpyLoader:
        def __init__(self):
            self.read_count = 0

        def iter_lines(self, path):
            for line in ["first", "", "second"]:
                self.read_count += 1
                yield line

    loader = SpyLoader()
    service = StreamingIngestionService(loader)

    generator = service.iter_ingest("unused.txt")

    assert loader.read_count == 0

    assert next(generator) == "first"
    assert loader.read_count == 1

    assert list(generator) == ["second"]
    assert loader.read_count == 3