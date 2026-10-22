
"""SQLite persistence for the Document Q&A API (Day 008)."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (trim(email) <> '')
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL CHECK (trim(filename) <> ''),
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'upload',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
"""


@dataclass(frozen=True)
class DocumentRecord:
    id: int
    user_id: int
    filename: str
    content: str
    source: str


@dataclass(frozen=True)
class ChunkRecord:
    id: int
    document_id: int
    chunk_index: int
    content: str


@dataclass(frozen=True)
class DocumentSummary:
    document_id: int
    filename: str
    owner_email: str
    chunk_count: int


class DocumentStore:
    """Owns a SQLite connection and provides document persistence operations."""

    def __init__(self, database_path: str | Path) -> None:
        self._connection = sqlite3.connect(str(database_path))
        self._connection.row_factory = sqlite3.Row

        # Enable foreign key enforcement on every connection.
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(SCHEMA_SQL)

    def close(self) -> None:
        self._connection.close()

    def create_user(self, email: str) -> int:
        with self._connection:
            cursor = self._connection.execute(
                "INSERT INTO users (email) VALUES (?)", (email,)
            )
        return int(cursor.lastrowid)

    def create_document(
        self,
        user_id: int,
        filename: str,
        content: str,
        source: str = "upload",
    ) -> int:
        with self._connection:
            cursor = self._connection.execute(
                """INSERT INTO documents (user_id, filename, content, source)
                   VALUES (?, ?, ?, ?)""",
                (user_id, filename, content, source),
            )
        return int(cursor.lastrowid)

    def get_document(self, document_id: int) -> DocumentRecord | None:
        row = self._connection.execute(
            """SELECT id, user_id, filename, content, source
               FROM documents WHERE id = ?""",
            (document_id,),
        ).fetchone()

        return DocumentRecord(**dict(row)) if row is not None else None

    def update_document(self, document_id: int, content: str) -> bool:
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE documents SET content = ? WHERE id = ?",
                (content, document_id),
            )

            if cursor.rowcount:
                # Old chunks no longer match updated document text.
                self._connection.execute(
                    "DELETE FROM chunks WHERE document_id = ?",
                    (document_id,),
                )

        return cursor.rowcount == 1

    def delete_document(self, document_id: int) -> bool:
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
        return cursor.rowcount == 1

    def add_chunk(
        self,
        document_id: int,
        chunk_index: int,
        content: str,
    ) -> int:
        with self._connection:
            cursor = self._connection.execute(
                """INSERT INTO chunks (document_id, chunk_index, content)
                   VALUES (?, ?, ?)""",
                (document_id, chunk_index, content),
            )
        return int(cursor.lastrowid)

    def get_chunks(self, document_id: int) -> list[ChunkRecord]:
        rows = self._connection.execute(
            """SELECT id, document_id, chunk_index, content
               FROM chunks WHERE document_id = ?
               ORDER BY chunk_index""",
            (document_id,),
        ).fetchall()

        return [ChunkRecord(**dict(row)) for row in rows]

    def list_document_summaries(self) -> list[DocumentSummary]:
        """Return one result per document, including documents with no chunks."""
        rows = self._connection.execute(
            """SELECT d.id AS document_id,
                      d.filename,
                      u.email AS owner_email,
                      COUNT(c.id) AS chunk_count
               FROM documents AS d
               JOIN users AS u ON u.id = d.user_id
               LEFT JOIN chunks AS c ON c.document_id = d.id
               GROUP BY d.id, d.filename, u.email
               ORDER BY d.id"""
        ).fetchall()

        return [DocumentSummary(**dict(row)) for row in rows]
