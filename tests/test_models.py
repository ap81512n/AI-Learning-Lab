
import pytest
from pydantic import ValidationError

from fde_learning_lab.models import (
    DocumentMetadata,
    IngestionRequest,
)


def valid_payload() -> dict:
    return {
        "document": {
            "filename": "employee_policy.pdf",
            "size_bytes": 4096,
            "department": "HR",
            "tags": ["internal", "policy"],
        },
        "chunk_size": 1000,
        "chunk_overlap": 150,
    }


def test_valid_request():
    request = IngestionRequest.model_validate(
        valid_payload()
    )
    assert request.document.size_bytes == 4096


@pytest.mark.parametrize(
    "bad_size", [0, -500, "4096"]
)
def test_invalid_file_size(bad_size):
    payload = valid_payload()
    payload["document"]["size_bytes"] = bad_size

    with pytest.raises(ValidationError):
        IngestionRequest.model_validate(payload)


def test_reject_non_pdf():
    payload = valid_payload()
    payload["document"]["filename"] = "policy.txt"

    with pytest.raises(ValidationError):
        IngestionRequest.model_validate(payload)


def test_reject_excessive_overlap():
    payload = valid_payload()
    payload["chunk_overlap"] = 1000

    with pytest.raises(ValidationError):
        IngestionRequest.model_validate(payload)


def test_reject_unknown_fields():
    payload = valid_payload()
    payload["document"]["unknown"] = "surprise"

    with pytest.raises(ValidationError):
        IngestionRequest.model_validate(payload)


def test_tags_not_shared():
    a = DocumentMetadata(
        filename="a.pdf",
        size_bytes=10,
        department="HR",
    )
    b = DocumentMetadata(
        filename="b.pdf",
        size_bytes=10,
        department="HR",
    )

    a.tags.append("internal")
    assert b.tags == []
