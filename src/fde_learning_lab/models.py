
from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


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
