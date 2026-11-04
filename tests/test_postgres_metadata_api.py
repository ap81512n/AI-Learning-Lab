
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fde_learning_lab.api import create_app
from fde_learning_lab.postgres_metadata import (
    MetadataRecord,
    get_metadata_store,
)


class FakeMetadataStore:
    def __init__(self):
        self.records = {}

    def save(self, metadata):
        record = MetadataRecord(
            **metadata.model_dump(),
            created_at=datetime.now(timezone.utc),
        )
        self.records[record.document_id] = record
        return record

    def get(self, document_id):
        return self.records.get(document_id)


def test_metadata_create_and_retrieve(tmp_path):
    app = create_app(database_path=tmp_path / "test.sqlite3")
    fake_store = FakeMetadataStore()

    app.dependency_overrides[get_metadata_store] = lambda: fake_store

    with TestClient(app) as client:
        created = client.post(
            "/metadata/documents",
            json={
                "document_id": "doc-001",
                "filename": "sample.pdf",
                "size_bytes": 1024,
            },
        )

        assert created.status_code == 201

        retrieved = client.get("/metadata/documents/doc-001")

        assert retrieved.status_code == 200
        assert retrieved.json()["filename"] == "sample.pdf"
        assert retrieved.json()["size_bytes"] == 1024

        missing = client.get("/metadata/documents/missing")
        assert missing.status_code == 404


def test_metadata_rejects_negative_size(tmp_path):
    app = create_app(database_path=tmp_path / "test.sqlite3")

    with TestClient(app) as client:
        response = client.post(
            "/metadata/documents",
            json={
                "document_id": "doc-002",
                "filename": "sample.pdf",
                "size_bytes": -1,
            },
        )

    assert response.status_code == 422
