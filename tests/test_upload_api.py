import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fde_learning_lab.api import create_app
from fde_learning_lab.upload_api import (
    UploadSettings,
    get_upload_settings,
)


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(
        database_path=tmp_path / "test.sqlite3"
    )

    # Override the real configuration for tests
    app.dependency_overrides[get_upload_settings] = (
        lambda: UploadSettings(
            upload_dir=tmp_path / "uploads",
            max_bytes=32,
        )
    )

    with TestClient(app) as test_client:
        yield test_client


def test_valid_pdf_is_saved(client, tmp_path):
    pdf = b"%PDF-1.4\nTest content"

    response = client.post(
        "/documents/upload",
        data={"title": "Medical document"},
        files={
            "file": (
                "report.pdf",
                pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["title"] == "Medical document"
    assert body["size_bytes"] == len(pdf)
    assert body["status"] == "uploaded"

    folder = tmp_path / "uploads"

    assert (
        folder / f"{body['upload_id']}.pdf"
    ).read_bytes() == pdf

    metadata = json.loads(
        (folder / f"{body['upload_id']}.json").read_text()
    )
    assert metadata["filename"] == "report.pdf"


@pytest.mark.parametrize(
    "filename,content_type,payload",
    [
        ("notes.txt", "text/plain", b"hello"),
        (
            "misnamed.pdf",
            "text/plain",
            b"%PDF-1.4\nhi",
        ),
        (
            "fake.pdf",
            "application/pdf",
            b"not actually a PDF",
        ),
    ],
)
def test_rejects_unsupported_files(
    client, tmp_path, filename, content_type, payload
):
    response = client.post(
        "/documents/upload",
        data={"title": "Test"},
        files={
            "file": (filename, payload, content_type)
        },
    )

    assert response.status_code == 415
    assert not list((tmp_path / "uploads").glob("*"))


def test_rejects_oversized_pdf(client, tmp_path):
    response = client.post(
        "/documents/upload",
        data={"title": "Test"},
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"x" * 40,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert not list((tmp_path / "uploads").glob("*"))


def test_rejects_blank_title(client):
    response = client.post(
        "/documents/upload",
        data={"title": "   "},
        files={
            "file": (
                "file.pdf",
                b"%PDF-1.4\n",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422


def test_rejects_missing_title(client):
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "file.pdf",
                b"%PDF-1.4\n",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422


def test_filename_cannot_escape_uploads(client, tmp_path):
    response = client.post(
        "/documents/upload",
        data={"title": "Safe path"},
        files={
            "file": (
                "../../unsafe.pdf",
                b"%PDF-1.4\n",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["filename"] == "unsafe.pdf"
    assert (
        tmp_path / "uploads" / f"{body['upload_id']}.pdf"
    ).exists()

    assert not (tmp_path / "unsafe.pdf").exists()


def test_cors_preflight(client):
    response = client.options(
        "/documents/upload",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:3000"
    )