"""Question-answering endpoint over uploaded PDFs."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fde_learning_lab.llm.adapter import ModelCallError
from fde_learning_lab.qa.document_qa import (
    InvalidModelOutput,
    answer_document,
)
from fde_learning_lab.qa.pdf_pages import (
    PdfExtractionError,
    extract_pdf_pages,
)
from fde_learning_lab.upload_api import (
    UploadSettings,
    get_upload_settings,
)

router = APIRouter(tags=["qa"])


class AskRequest(BaseModel):
    upload_id: str = Field(min_length=1, max_length=64, pattern=r"^[0-9a-f]+$")
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    answer: str
    page_ids: list[int]
    refused: bool


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    request: Request,
    settings: Annotated[UploadSettings, Depends(get_upload_settings)],
) -> AskResponse:
    # The pattern constraint keeps the ID hex-only, so no path traversal.
    pdf_path = settings.upload_dir / f"{body.upload_id}.pdf"

    if not pdf_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    try:
        pages = extract_pdf_pages(pdf_path)
    except PdfExtractionError:
        raise HTTPException(
            status_code=422,
            detail="Stored PDF could not be read",
        ) from None

    try:
        result = answer_document(
            question=body.question,
            pages=pages,
            model=request.app.state.model_adapter,
        )
    except ValueError:
        raise HTTPException(
            status_code=413,
            detail="Document exceeds context limit",
        ) from None
    except InvalidModelOutput:
        raise HTTPException(
            status_code=502,
            detail="Invalid model response",
        ) from None
    except ModelCallError:
        raise HTTPException(
            status_code=503,
            detail="Model provider unavailable",
        ) from None

    return AskResponse(
        answer=result.answer,
        page_ids=result.page_ids,
        refused=result.refused,
    )
