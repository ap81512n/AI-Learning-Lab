
"""Day 009: advanced SQL version ranking, safe binding, and query planning."""

import sqlite3
from pathlib import Path

import pytest

from fde_learning_lab.db import DocumentStore
from fde_learning_lab.sql_queries import DocumentVersionQueries


@pytest.fixture
def stores(tmp_path: Path):
    database_path = tmp_path / "day009.db"
    documents = DocumentStore(database_path)
    queries = DocumentVersionQueries(database_path)

    yield documents, queries

    queries.close()
    documents.close()


def test_cte_returns_latest_version_per_document(stores):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")
    report_id = documents.create_document(
        user_id, "report.txt", "current report"
    )
    notes_id = documents.create_document(
        user_id, "notes.txt", "current notes"
    )

    queries.add_version(report_id, 2, "report version two")
    queries.add_version(report_id, 1, "report version one")
    queries.add_version(notes_id, 1, "notes version one")

    latest = queries.latest_versions_for_user(user_id)

    assert [(v.document_id, v.version_number) for v in latest] == [
        (report_id, 2),
        (notes_id, 1),
    ]
    assert latest[0].content == "report version two"


def test_latest_versions_are_filtered_to_user(stores):
    documents, queries = stores
    alice = documents.create_user("alice@example.com")
    bob = documents.create_user("bob@example.com")

    alice_doc = documents.create_document(
        alice, "private.txt", "alice"
    )
    bob_doc = documents.create_document(
        bob, "private.txt", "bob"
    )

    queries.add_version(alice_doc, 1, "alice version")
    queries.add_version(bob_doc, 1, "bob version")

    assert [
        v.document_id
        for v in queries.latest_versions_for_user(alice)
    ] == [alice_doc]

    assert [
        v.document_id
        for v in queries.latest_versions_for_user(bob)
    ] == [bob_doc]


def test_aggregation_includes_documents_with_zero_versions(stores):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")

    first = documents.create_document(
        user_id, "first.txt", "first"
    )
    second = documents.create_document(
        user_id, "second.txt", "second"
    )

    queries.add_version(first, 1, "first v1")
    queries.add_version(first, 2, "first v2")

    counts = queries.version_counts_for_user(user_id)

    assert [(item.document_id, item.count) for item in counts] == [
        (first, 2),
        (second, 0),
    ]


def test_duplicate_version_number_is_rejected(stores):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")
    doc_id = documents.create_document(
        user_id, "readme.txt", "content"
    )

    queries.add_version(doc_id, 1, "original")

    with pytest.raises(sqlite3.IntegrityError):
        queries.add_version(doc_id, 1, "duplicate")


def test_invalid_document_id_is_rejected_by_foreign_key(stores):
    _, queries = stores

    with pytest.raises(sqlite3.IntegrityError):
        queries.add_version(999_999, 1, "orphan")


def test_parameter_binding_does_not_execute_injected_sql(stores):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")
    doc_id = documents.create_document(
        user_id, "notes.txt", "content"
    )

    assert queries.find_document_ids_by_filename(
        "notes.txt"
    ) == [doc_id]

    assert queries.find_document_ids_by_filename(
        "notes.txt' OR 1=1 --"
    ) == []


def test_explain_query_plan_changes_after_adding_filename_index(stores):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")
    documents.create_document(
        user_id, "notes.txt", "content"
    )

    before = " ".join(
        queries.explain_filename_lookup("notes.txt")
    )

    queries.create_filename_index()

    after = " ".join(
        queries.explain_filename_lookup("notes.txt")
    )

    assert "idx_documents_filename" not in before
    assert "idx_documents_filename" in after


def test_document_delete_cascades_to_version_history(stores):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")
    doc_id = documents.create_document(
        user_id, "old.txt", "old"
    )

    queries.add_version(doc_id, 1, "archived")
    assert documents.delete_document(doc_id) is True

    assert queries.latest_versions_for_user(user_id) == []


def test_versions_remain_after_reopening_database(stores, tmp_path):
    documents, queries = stores
    user_id = documents.create_user("alice@example.com")
    doc_id = documents.create_document(
        user_id, "persist.txt", "saved"
    )

    queries.add_version(doc_id, 1, "persistent version")

    # A second connection verifies disk persistence.
    with sqlite3.connect(tmp_path / "day009.db") as db:
        row = db.execute(
            "SELECT content FROM document_versions WHERE document_id = ?",
            (doc_id,),
        ).fetchone()

        assert row == ("persistent version",)
