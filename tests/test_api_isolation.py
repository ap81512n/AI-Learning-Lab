from pathlib import Path
from fastapi.testclient import TestClient
from fde_learning_lab.upload_api import get_upload_settings


PDF_HEADER = b"%PDF-1.7\n"


def make_pdf_bytes(size: int) -> bytes:
    """Create bytes accepted by our current PDF header validator."""
    if size < len(PDF_HEADER):
        raise ValueError("Size must fit the PDF header")

    return PDF_HEADER + b"x" * (size - len(PDF_HEADER))


def post_upload(
    client: TestClient,
    payload: bytes,
    filename: str = "report.pdf",
    title: str = "Test report",
):
    """Reusable helper for sending PDF uploads."""
    return client.post(
        "/documents/upload",
        data={"title": title},
        files={
            "file": (
                filename,
                payload,
                "application/pdf",
            )
        },
    )


def test_missing_file_returns_422(
    isolated_client: TestClient,
    isolated_upload_dir: Path,
):
    response = isolated_client.post(
        "/documents/upload",
        data={"title": "Missing file"},
    )

    assert response.status_code == 422
    assert list(isolated_upload_dir.glob("*")) == []


def test_fake_pdf_signature_returns_415(
    isolated_client: TestClient,
    isolated_upload_dir: Path,
):
    response = post_upload(
        isolated_client,
        payload=b"This is not a PDF",
    )

    assert response.status_code == 415
    assert list(isolated_upload_dir.glob("*")) == []


def test_exact_size_limit_is_accepted(
    isolated_client: TestClient,
    isolated_upload_dir: Path,
):
    payload = make_pdf_bytes(32)

    response = post_upload(
        isolated_client,
        payload=payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["size_bytes"] == 32
    assert body["status"] == "uploaded"

    saved_pdf = (
        isolated_upload_dir / f"{body['upload_id']}.pdf"
    )

    assert saved_pdf.read_bytes() == payload


def test_one_byte_over_limit_returns_413(
    isolated_client: TestClient,
    isolated_upload_dir: Path,
):
    payload = make_pdf_bytes(33)

    response = post_upload(
        isolated_client,
        payload=payload,
    )

    assert response.status_code == 413

    # Invalid uploads must not leave partial files.
    assert list(isolated_upload_dir.glob("*")) == []


def test_duplicate_filename_does_not_overwrite(
    isolated_client: TestClient,
    isolated_upload_dir: Path,
):
    first_payload = make_pdf_bytes(20)
    second_payload = make_pdf_bytes(24)

    first_response = post_upload(
        isolated_client,
        first_payload,
        filename="duplicate.pdf",
    )

    second_response = post_upload(
        isolated_client,
        second_payload,
        filename="duplicate.pdf",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_id = first_response.json()["upload_id"]
    second_id = second_response.json()["upload_id"]

    assert first_id != second_id

    assert (
        isolated_upload_dir / f"{first_id}.pdf"
    ).read_bytes() == first_payload

    assert (
        isolated_upload_dir / f"{second_id}.pdf"
    ).read_bytes() == second_payload

    assert len(list(isolated_upload_dir.glob("*.pdf"))) == 2
    assert len(list(isolated_upload_dir.glob("*.json"))) == 2


def test_upload_directory_from_environment(
    monkeypatch,
    tmp_path: Path,
):
    test_directory = tmp_path / "custom_uploads"

    monkeypatch.setenv(
        "FDE_UPLOAD_DIR",
        str(test_directory),
    )

    settings = get_upload_settings()

    assert settings.upload_dir == test_directory