from __future__ import annotations

from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from fde_learning_lab.exceptions import DocumentError


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    filename: str = Field(
        min_length=5,
        pattern=r"(?i)\.pdf$",
    )

    size_bytes: int = Field(gt=0)

    department: str = Field(min_length=2)

    tags: list[str] = Field(default_factory=list)


class IngestionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    document: DocumentMetadata

    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=4000,
    )

    chunk_overlap: int = Field(
        default=200,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> IngestionRequest:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )
        return self


class IngestedDocument(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )

    path: Path

    content: str

    @computed_field
    @property
    def char_count(self) -> int:
        return len(self.content)


class IngestionFailure(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )

    path: Path

    error_type: str

    message: str

    @classmethod
    def from_exception(
        cls,
        path: Path,
        exc: DocumentError,
    ) -> IngestionFailure:
        return cls(
            path=path,
            error_type=type(exc).__name__,
            message=exc.message,
        )


class IngestionResult(BaseModel):
    documents: list[IngestedDocument] = Field(
        default_factory=list,
    )

    failures: list[IngestionFailure] = Field(
        default_factory=list,
    )

    @computed_field
    @property
    def ok(self) -> bool:
        return not self.failures