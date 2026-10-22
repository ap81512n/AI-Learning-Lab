
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from fde_learning_lab.db import DocumentStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[DocumentStore]:
    database = DocumentStore(tmp_path / "test_documents.sqlite3")
    try:
        yield database
    finally:
        database.close()


def test_create_and_read_document(store: DocumentStore) -> None:
    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(
        user_id, "notes.txt", "Hello SQL", "file"
    )

    document = store.get_document(document_id)

    assert document is not None
    assert document.filename == "notes.txt"
    assert document.content == "Hello SQL"
    assert document.source == "file"
    assert document.user_id == user_id


def test_update_and_delete_document(store: DocumentStore) -> None:
    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(user_id, "notes.txt", "Before")

    assert store.update_document(document_id, "After") is True
    assert store.get_document(document_id).content == "After"

    assert store.delete_document(document_id) is True
    assert store.get_document(document_id) is None

    assert store.update_document(document_id, "Again") is False
    assert store.delete_document(document_id) is False


def test_updating_document_clears_outdated_chunks(
    store: DocumentStore,
) -> None:
    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(user_id, "notes.txt", "Old")
    store.add_chunk(document_id, 0, "Old")

    assert store.update_document(document_id, "New") is True
    assert store.get_chunks(document_id) == []


def test_chunks_are_returned_in_position_order(
    store: DocumentStore,
) -> None:
    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(user_id, "notes.txt", "A B")

    store.add_chunk(document_id, 1, "B")
    store.add_chunk(document_id, 0, "A")

    assert [c.content for c in store.get_chunks(document_id)] == ["A", "B"]


def test_join_returns_zero_or_more_chunks_without_duplicates(
    store: DocumentStore,
) -> None:
    user_id = store.create_user("alice@example.com")
    empty_id = store.create_document(user_id, "empty.txt", "")
    full_id = store.create_document(user_id, "full.txt", "one two")

    store.add_chunk(full_id, 0, "one")
    store.add_chunk(full_id, 1, "two")

    summaries = store.list_document_summaries()

    assert [s.document_id for s in summaries] == [empty_id, full_id]
    assert [s.chunk_count for s in summaries] == [0, 2]
    assert all(s.owner_email == "alice@example.com" for s in summaries)


def test_unknown_foreign_keys_are_rejected(
    store: DocumentStore,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        store.create_document(99999, "orphan.txt", "unowned")

    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(user_id, "owned.txt", "valid")

    with pytest.raises(sqlite3.IntegrityError):
        store.add_chunk(document_id + 99999, 0, "orphan chunk")


def test_chunk_positions_cannot_repeat_per_document(
    store: DocumentStore,
) -> None:
    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(user_id, "a.txt", "ab")

    store.add_chunk(document_id, 0, "a")

    with pytest.raises(sqlite3.IntegrityError):
        store.add_chunk(document_id, 0, "b")


def test_deleting_document_cascades_to_chunks(
    store: DocumentStore,
) -> None:
    user_id = store.create_user("alice@example.com")
    document_id = store.create_document(user_id, "a.txt", "a")

    store.add_chunk(document_id, 0, "a")

    assert store.delete_document(document_id) is True
    assert store.get_chunks(document_id) == []


def test_data_persists_after_reopening(tmp_path: Path) -> None:
    path = tmp_path / "persistent.sqlite3"

    first = DocumentStore(path)
    try:
        user_id = first.create_user("alice@example.com")
        document_id = first.create_document(user_id, "notes.txt", "saved")
    finally:
        first.close()

    second = DocumentStore(path)
    try:
        assert second.get_document(document_id).content == "saved"
    finally:
        second.close()


def test_user_id_index_exists(tmp_path: Path) -> None:
    path = tmp_path / "indexed.sqlite3"
    database = DocumentStore(path)
    database.close()

    connection = sqlite3.connect(path)
    try:
        indexes = connection.execute(
            "PRAGMA index_list('documents')"
        ).fetchall()
    finally:
        connection.close()

    assert "idx_documents_user_id" in {row[1] for row in indexes}


def test_sql_metacharacters_are_stored_as_text(
    store: DocumentStore,
) -> None:
    user_id = store.create_user("alice@example.com")
    suspicious_text = "Hi'); DROP TABLE users; --"

    document_id = store.create_document(
        user_id, "note.txt", suspicious_text
    )

    assert store.get_document(document_id).content == suspicious_text
    assert store.create_user("bob@example.com") > 0
