from pathlib import Path

from fde_learning_lab.loaders import TextLoader

def test_load_text_file(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("Hello FDE", encoding="utf-8")

    loader = TextLoader()

    assert loader.load(path) == "Hello FDE"

def test_load_incorrect_text_file(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("Hello FDE", encoding="utf-8")

    loader = TextLoader()

    assert loader.load(path) == "Hello 123"

