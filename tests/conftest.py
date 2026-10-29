from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fde_learning_lab.api import create_app
from fde_learning_lab.upload_api import (
    UploadSettings,
    get_upload_settings,
)


@pytest.fixture
def isolated_upload_dir(tmp_path: Path) -> Path:
    """Give each test a separate upload directory."""
    return tmp_path / "uploads"


@pytest.fixture
def isolated_client(
    tmp_path: Path,
    isolated_upload_dir: Path,
) -> Iterator[TestClient]:
    """Create an API with isolated database and upload storage."""

    app = create_app(
        database_path=tmp_path / "test.sqlite3"
    )

    # Replace production settings with test settings.
    app.dependency_overrides[get_upload_settings] = (
        lambda: UploadSettings(
            upload_dir=isolated_upload_dir,
            max_bytes=32,
        )
    )

    with TestClient(app) as client:
        yield client

    # Remove overrides when the test finishes.
    app.dependency_overrides.clear()