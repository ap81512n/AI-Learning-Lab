
"""API tests for Day 010."""

from contextlib import closing
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from fde_learning_lab.api import create_app
from fde_learning_lab.db import DocumentStore


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[tuple[TestClient, int]]:
    database_path = tmp_path / "day010.sqlite3"

    with closing(DocumentStore(database_path)) as store:
        user_id = store.create_user("abc@example.com")

    with TestClient(create_app(database_path)) as client:
        yield client, user_id


def test_health(api_client: tuple[TestClient, int]) -> None:
    client, _ = api_client
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_documents_initially_empty(
    api_client: tuple[TestClient, int],
) -> None:
    client, _ = api_client
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []


def test_create_then_read_and_list_document(
    api_client: tuple[TestClient, int],
) -> None:
    client, user_id = api_client

    payload = {
        "user_id": user_id,
        "filename": "notes.txt",
        "content": "FastAPI",
    }

    created = client.post("/documents", json=payload)

    assert created.status_code == 201

    body = created.json()
    assert isinstance(body["id"], int)
    assert body["user_id"] == user_id
    assert body["source"] == "api"

    fetched = client.get(f"/documents/{body['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == body

    summaries = client.get("/documents")

    assert summaries.status_code == 200
    assert summaries.json() == [
        {
            "document_id": body["id"],
            "filename": "notes.txt",
            "owner_email": "abc@example.com",
            "chunk_count": 0,
        }
    ]


def test_missing_document_returns_404(
    api_client: tuple[TestClient, int],
) -> None:
    client, _ = api_client
    response = client.get("/documents/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


@pytest.mark.parametrize("document_id", ["abc", "0", "-2"])
def test_invalid_path_returns_422(
    api_client: tuple[TestClient, int],
    document_id: str,
) -> None:
    client, _ = api_client
    response = client.get(f"/documents/{document_id}")

    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"user_id": 0},
        {"filename": ""},
        {"content": ""},
    ],
)
def test_invalid_body_returns_422(
    api_client: tuple[TestClient, int],
    overrides: dict[str, object],
) -> None:
    client, user_id = api_client

    payload = {
        "user_id": user_id,
        "filename": "notes.txt",
        "content": "ok",
    }
    payload.update(overrides)

    response = client.post("/documents", json=payload)

    assert response.status_code == 422


def test_nonexistent_user_id_returns_422(
    api_client: tuple[TestClient, int],
) -> None:
    client, _ = api_client

    response = client.post(
        "/documents",
        json={
            "user_id": 999999,
            "filename": "notes.txt",
            "content": "ok",
        },
    )

    assert response.status_code == 422


def test_openapi_lists_document_routes(
    api_client: tuple[TestClient, int],
) -> None:
    client, _ = api_client
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "get" in paths["/health"]
    assert {"get", "post"} <= set(paths["/documents"])
    assert "get" in paths["/documents/{document_id}"]
