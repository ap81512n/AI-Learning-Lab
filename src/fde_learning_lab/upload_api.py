"""Validated PDF upload endpoint."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

import aiofiles
from fastapi import (
    APIRouter, Depends, File, Form,
    HTTPException, UploadFile, status,
)
from pydantic import BaseModel


@dataclass(frozen=True)
class UploadSettings:
    upload_dir: Path
    max_bytes: int = 5 * 1024 * 1024  # 5 MiB


def get_upload_settings() -> UploadSettings:
    return UploadSettings(
        upload_dir=Path(
            os.getenv("FDE_UPLOAD_DIR", "data/uploads")
        )
    )


class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    title: str
    size_bytes: int
    status: Literal["uploaded"] = "uploaded"


router = APIRouter(tags=["uploads"])


@router.post(
    "/documents/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    file: Annotated[
        UploadFile, File(description="PDF file, max 5 MiB")
    ],
    title: Annotated[
        str, Form(min_length=1, max_length=120)
    ],
    settings: Annotated[
        UploadSettings, Depends(get_upload_settings)
    ],
) -> UploadResponse:
    stored_path: Path | None = None
    metadata_path: Path | None = None

    try:
        # Validate title and filename
        clean_title = title.strip()
        if not clean_title:
            raise HTTPException(
                status_code=422,
                detail="Title cannot be blank",
            )

        filename = (
            (file.filename or "")
            .replace("\\", "/")
            .rsplit("/", 1)[-1]
        )

        if (
            not filename.lower().endswith(".pdf")
            or file.content_type != "application/pdf"
        ):
            raise HTTPException(
                status_code=415,
                detail="Only PDF uploads are allowed",
            )

        # Basic content signature verification
        if await file.read(5) != b"%PDF-":
            raise HTTPException(
                status_code=415,
                detail="Invalid PDF signature",
            )

        await file.seek(0)

        # Store with a generated ID, not the user's filename
        settings.upload_dir.mkdir(
            parents=True, exist_ok=True
        )

        upload_id = uuid4().hex
        stored_path = (
            settings.upload_dir / f"{upload_id}.pdf"
        )
        metadata_path = (
            settings.upload_dir / f"{upload_id}.json"
        )

        # Stream the file in chunks with a size limit
        size_bytes = 0

        async with aiofiles.open(
            stored_path, "xb"
        ) as destination:
            while chunk := await file.read(64 * 1024):
                size_bytes += len(chunk)

                if size_bytes > settings.max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="PDF exceeds maximum upload size",
                    )

                await destination.write(chunk)

        result = UploadResponse(
            upload_id=upload_id,
            filename=filename,
            title=clean_title,
            size_bytes=size_bytes,
        )

        # Persist upload metadata until DB integration
        async with aiofiles.open(
            metadata_path, "x", encoding="utf-8"
        ) as metadata:
            await metadata.write(
                result.model_dump_json(indent=2)
            )

        return result

    except Exception:
        # Never leave partial files after failure
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        if metadata_path is not None:
            metadata_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()