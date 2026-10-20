"""End-to-end acceptance tests for the document CLI."""

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fde_learning_lab.document_cli",
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_returns_document_metadata(tmp_path: Path) -> None:
    document = tmp_path / "example.txt"
    document.write_text(
        "Hello FDE\nLearn Python\n",
        encoding="utf-8",
    )

    result = run_cli(str(document))

    assert result.returncode == 0

    assert json.loads(result.stdout) == {
        "filename": "example.txt",
        "characters": 23,
        "words": 4,
        "lines": 2,
    }

    assert result.stderr == ""


def test_cli_pretty_option_indents_json(tmp_path: Path) -> None:
    document = tmp_path / "example.txt"
    document.write_text("Hello, how is it going", encoding="utf-8")

    result = run_cli(str(document), "--pretty")

    assert result.returncode == 0
    assert '\n  "filename"' in result.stdout
    assert json.loads(result.stdout)["words"] == 5


def test_cli_verbose_logs_to_stderr_not_stdout(
    tmp_path: Path,
) -> None:
    document = tmp_path / "example.txt"
    document.write_text("Hello FDE", encoding="utf-8")

    result = run_cli("--verbose", str(document))

    assert result.returncode == 0
    assert "DEBUG:" in result.stderr
    assert json.loads(result.stdout)["words"] == 2


def test_cli_missing_file_returns_error(tmp_path: Path) -> None:
    result = run_cli(str(tmp_path / "missing.txt"))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Cannot read file" in result.stderr


def test_cli_directory_returns_error(tmp_path: Path) -> None:
    result = run_cli(str(tmp_path))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Cannot read file" in result.stderr


def test_cli_invalid_utf8_returns_error(tmp_path: Path) -> None:
    document = tmp_path / "binary.txt"
    document.write_bytes(b"\xff\xfe")

    result = run_cli(str(document))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Cannot read file" in result.stderr


def test_cli_help_displays_usage() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--pretty" in result.stdout
    assert "--verbose" in result.stdout
