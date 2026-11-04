
import os
from datetime import datetime
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel, Field


class MetadataCreate(BaseModel):
    document_id: str = Field(min_length=1, max_length=128)
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)


class MetadataRecord(MetadataCreate):
    created_at: datetime


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS document_metadata (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class PostgresMetadataStore:
    def _connect(self):
        return psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            dbname=os.getenv("POSTGRES_DB", "fde_lab"),
            user=os.getenv("POSTGRES_USER", "fde_user"),
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=5,
            row_factory=dict_row,
        )

    def save(self, metadata: MetadataCreate) -> MetadataRecord:
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)
            row = conn.execute(
                """
                INSERT INTO document_metadata
                    (document_id, filename, size_bytes)
                VALUES (%s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    size_bytes = EXCLUDED.size_bytes
                RETURNING
                    document_id, filename, size_bytes, created_at
                """,
                (
                    metadata.document_id,
                    metadata.filename,
                    metadata.size_bytes,
                ),
            ).fetchone()

        return MetadataRecord.model_validate(row)

    def get(self, document_id: str) -> MetadataRecord | None:
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)
            row = conn.execute(
                """
                SELECT document_id, filename, size_bytes, created_at
                FROM document_metadata
                WHERE document_id = %s
                """,
                (document_id,),
            ).fetchone()

        return MetadataRecord.model_validate(row) if row else None


def get_metadata_store() -> PostgresMetadataStore:
    return PostgresMetadataStore()


router = APIRouter(prefix="/metadata", tags=["PostgreSQL Metadata"])

StoreDependency = Annotated[
    PostgresMetadataStore,
    Depends(get_metadata_store),
]


@router.post("/documents", response_model=MetadataRecord, status_code=201)
def save_metadata(metadata: MetadataCreate, store: StoreDependency):
    try:
        return store.save(metadata)
    except (psycopg.Error, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Metadata database unavailable",
        ) from exc


@router.get("/documents/{document_id}", response_model=MetadataRecord)
def get_metadata(document_id: str, store: StoreDependency):
    try:
        record = store.get(document_id)
    except (psycopg.Error, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Metadata database unavailable",
        ) from exc

    if record is None:
        raise HTTPException(status_code=404, detail="Metadata not found")

    return record
