
"""HTTP endpoints for Project 1's document store."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Path as PathParameter, status
from pydantic import BaseModel, Field
from fde_learning_lab.db import DocumentRecord, DocumentStore
from fastapi.middleware.cors import CORSMiddleware
from fde_learning_lab.graphql_api import graphql_router
from fde_learning_lab.upload_api import (
    router as upload_router,
)


# 1. Request and response schemas

class HealthResponse(BaseModel):
    status: Literal["ok"]


class DocumentCreate(BaseModel):
    user_id: int = Field(gt=0)
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: str = Field(default="api", min_length=1)


class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    content: str
    source: str


class DocumentSummaryResponse(BaseModel):
    document_id: int
    filename: str
    owner_email: str
    chunk_count: int


def to_document_response(record: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=record.id,
        user_id=record.user_id,
        filename=record.filename,
        content=record.content,
        source=record.source,
    )


# 2. Application factory

def create_app(database_path: str | Path | None = None) -> FastAPI:
    """Create the API with a configurable SQLite database."""
    db_path = Path(
        database_path if database_path is not None
        else os.getenv("FDE_DB_PATH", "data/documents.sqlite3")
    )

    if str(db_path) == ":memory:":
        raise ValueError("Use a file-backed SQLite path for HTTP requests")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    application = FastAPI(
        title="Document Q&A API",
        version="0.1.0",
    )

    application.include_router(graphql_router, prefix="/graphql")

    application.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    )
    application.include_router(upload_router)

    # 3. Health endpoint

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    # 4. List document summaries

    @application.get(
        "/documents",
        response_model=list[DocumentSummaryResponse],
    )
    def list_documents() -> list[DocumentSummaryResponse]:
        with closing(DocumentStore(db_path)) as store:
            summaries = store.list_document_summaries()

        return [
            DocumentSummaryResponse(
                document_id=summary.document_id,
                filename=summary.filename,
                owner_email=summary.owner_email,
                chunk_count=summary.chunk_count,
            )
            for summary in summaries
        ]

    # 5. Get an individual document

    @application.get(
        "/documents/{document_id}",
        response_model=DocumentResponse,
    )
    def get_document(
        document_id: int = PathParameter(gt=0),
    ) -> DocumentResponse:
        with closing(DocumentStore(db_path)) as store:
            record = store.get_document(document_id)

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        return to_document_response(record)

    # 6. Create a new document

    @application.post(
        "/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_document(payload: DocumentCreate) -> DocumentResponse:
        with closing(DocumentStore(db_path)) as store:
            try:
                document_id = store.create_document(
                    user_id=payload.user_id,
                    filename=payload.filename,
                    content=payload.content,
                    source=payload.source,
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="Invalid user_id or document data",
                ) from exc

            record = store.get_document(document_id)

        if record is None:
            raise RuntimeError("Newly created document could not be loaded")

        return to_document_response(record)

    return application


# Entry point used by Uvicorn
app = create_app()
