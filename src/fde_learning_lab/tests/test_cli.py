
import sys

from fde_learning_lab import build_status, main


def test_build_status_default():
    result = build_status("demo-client")

    assert result == (
        "READY | client=demo-client "
        "| environment=development"
    )


def test_build_status_production():
    result = build_status(
        "demo-client",
        "production"
    )

    assert result == (
        "READY | client=demo-client "
        "| environment=production"
    )


def test_cli_production(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fde-learning-lab",
            "--client", "demo-client",
            "--environment", "production"
        ]
    )

    main()

    captured = capsys.readouterr()

    assert (
        "READY | client=demo-client "
        "| environment=production"
    ) in captured.out
