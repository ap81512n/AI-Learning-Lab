
import pytest
from fastapi.testclient import TestClient

from fde_learning_lab.api import create_app
from fde_learning_lab.graphql_api import (
    DocumentRow,
    OwnerRow,
    MockDocumentRepository,
    get_document_repository,
)


@pytest.fixture
def graphql_client(tmp_path):
    repository = MockDocumentRepository()

    app = create_app(
        database_path=tmp_path / "graphql_test.sqlite3"
    )

    app.dependency_overrides[get_document_repository] = (
        lambda: repository
    )

    with TestClient(app) as client:
        yield client, repository

    app.dependency_overrides.clear()


# Test 1: Retrieve all documents
def test_graphql_documents_query(graphql_client):
    client, repository = graphql_client

    query = """
    {
        documents {
            id
            filename
            ownerEmail
        }
    }
    """

    response = client.post(
        "/graphql", json={"query": query}
    )

    assert response.status_code == 200

    result = response.json()
    assert "errors" not in result

    documents = result["data"]["documents"]

    assert len(documents) == 3
    assert documents[0]["filename"] == "guide.pdf"
    assert documents[0]["ownerEmail"] == "dev@example.com"
    assert repository.query_count == 2


# Test 2: Verify field selection
def test_graphql_returns_only_requested_fields(graphql_client):
    client, _ = graphql_client

    query = """
    {
        documents {
            filename
        }
    }
    """

    response = client.post(
        "/graphql", json={"query": query}
    )

    assert response.status_code == 200

    documents = response.json()["data"]["documents"]

    assert len(documents) == 3

    for document in documents:
        assert list(document.keys()) == ["filename"]


# Test 3: Empty repository
def test_graphql_empty_documents(tmp_path):
    repository = MockDocumentRepository(
        documents=[],
        owners=[],
    )

    app = create_app(
        database_path=tmp_path / "empty.sqlite3"
    )
    app.dependency_overrides[get_document_repository] = (
        lambda: repository
    )

    with TestClient(app) as client:
        response = client.post(
            "/graphql",
            json={"query": "{ documents { id } }"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["documents"] == []
    assert repository.query_count == 1


# Test 4: Verify batch fetching prevents N+1
def test_graphql_avoids_n_plus_one(tmp_path):
    documents = [
        DocumentRow(
            id=i,
            filename=f"file-{i}.pdf",
            owner_id=101,
        )
        for i in range(1, 51)
    ]

    owners = [
        OwnerRow(id=101, email="owner@example.com")
    ]

    repository = MockDocumentRepository(
        documents=documents,
        owners=owners,
    )

    app = create_app(
        database_path=tmp_path / "batch.sqlite3"
    )

    app.dependency_overrides[get_document_repository] = (
        lambda: repository
    )

    with TestClient(app) as client:
        response = client.post(
            "/graphql",
            json={
                "query": "{ documents { id ownerEmail } }"
            },
        )

    assert response.status_code == 200

    result = response.json()
    assert "errors" not in result
    assert len(result["data"]["documents"]) == 50

    # Two repository fetches, not 51
    assert repository.query_count == 2


# Test 5: Existing REST endpoint still works
def test_existing_rest_endpoint(graphql_client):
    client, _ = graphql_client

    response = client.get("/health")

    assert response.status_code == 200
