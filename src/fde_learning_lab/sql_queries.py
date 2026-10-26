
"""Advanced, parameterized SQL for document version history (Day 009)."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LatestVersion:
    document_id: int
    filename: str
    version_number: int
    content: str


@dataclass(frozen=True)
class VersionCount:
    document_id: int
    filename: str
    count: int


class DocumentVersionQueries:
    """Query document versions stored alongside the Day 008 tables."""

    def __init__(self, database_path: str | Path) -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_versions (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL
                        REFERENCES documents(id) ON DELETE CASCADE,
                    version_number INTEGER NOT NULL CHECK (version_number > 0),
                    content TEXT NOT NULL,
                    UNIQUE (document_id, version_number)
                )
                """
            )

    def close(self) -> None:
        self.connection.close()

    def add_version(
        self, document_id: int, version_number: int, content: str
    ) -> int:
        """Insert an explicitly numbered version; duplicates are rejected."""
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO document_versions
                    (document_id, version_number, content)
                VALUES (?, ?, ?)
                """,
                (document_id, version_number, content),
            )
        return int(cursor.lastrowid)

    def latest_versions_for_user(self, user_id: int) -> list[LatestVersion]:
        """Use a CTE and window ranking to find each document's newest version."""
        rows = self.connection.execute(
            """
            WITH ranked_versions AS (
                SELECT
                    document_id,
                    version_number,
                    content,
                    ROW_NUMBER() OVER (
                        PARTITION BY document_id
                        ORDER BY version_number DESC
                    ) AS position
                FROM document_versions
            )
            SELECT d.id AS document_id,
                   d.filename,
                   r.version_number,
                   r.content
            FROM ranked_versions AS r
            JOIN documents AS d ON d.id = r.document_id
            WHERE d.user_id = ? AND r.position = 1
            ORDER BY d.id
            """,
            (user_id,),
        ).fetchall()

        return [
            LatestVersion(
                document_id=row["document_id"],
                filename=row["filename"],
                version_number=row["version_number"],
                content=row["content"],
            )
            for row in rows
        ]

    def version_counts_for_user(self, user_id: int) -> list[VersionCount]:
        """Count versions, including documents that have no versions yet."""
        rows = self.connection.execute(
            """
            SELECT d.id AS document_id,
                   d.filename,
                   COUNT(v.id) AS version_count
            FROM documents AS d
            LEFT JOIN document_versions AS v
                ON v.document_id = d.id
            WHERE d.user_id = ?
            GROUP BY d.id, d.filename
            ORDER BY d.id
            """,
            (user_id,),
        ).fetchall()

        return [
            VersionCount(
                document_id=row["document_id"],
                filename=row["filename"],
                count=row["version_count"],
            )
            for row in rows
        ]

    def find_document_ids_by_filename(self, filename: str) -> list[int]:
        """Treat even suspicious input as a value, never executable SQL."""
        rows = self.connection.execute(
            "SELECT id FROM documents WHERE filename = ? ORDER BY id",
            (filename,),
        ).fetchall()
        return [row["id"] for row in rows]

    def explain_filename_lookup(self, filename: str) -> list[str]:
        """Return SQLite's plan for the exact filename lookup."""
        rows = self.connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT id FROM documents WHERE filename = ?
            """,
            (filename,),
        ).fetchall()
        return [row["detail"] for row in rows]

    def create_filename_index(self) -> None:
        """Index exact filename lookups; leave it off until plan comparison."""
        with self.connection:
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_filename "
                "ON documents(filename)"
            )
