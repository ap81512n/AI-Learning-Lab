
import pandas as pd
import pytest

from fde_learning_lab.document_stats import summarize_upload_metrics


def test_summarize_uploads_with_outlier() -> None:
    uploads = pd.DataFrame(
        {
            "status": [
                "success", "success", "success",
                "failed", "success",
            ],
            "processing_ms": [100, 120, 110, None, 1000],
            "page_count": [1, 2, 3, None, 10],
        }
    )

    original = uploads.copy(deep=True)
    metrics = summarize_upload_metrics(uploads)

    assert metrics["total_uploads"] == 5
    assert metrics["successful_uploads"] == 4
    assert metrics["failed_uploads"] == 1
    assert metrics["failure_rate_pct"] == 20.0

    assert metrics["mean_processing_ms"] == pytest.approx(332.5)
    assert metrics["median_processing_ms"] == pytest.approx(115.0)
    assert metrics["variance_processing_ms2"] == pytest.approx(
        198091.6667
    )
    assert metrics["std_processing_ms"] == pytest.approx(
        445.0749
    )
    assert metrics["p95_processing_ms"] == pytest.approx(868.0)
    assert metrics["mean_page_count"] == pytest.approx(4.0)
    assert metrics["missing_success_timings"] == 0

    pd.testing.assert_frame_equal(uploads, original)


def test_missing_success_time_is_excluded() -> None:
    uploads = pd.DataFrame(
        {
            "status": ["success", "failed"],
            "processing_ms": ["not-a-number", None],
            "page_count": ["4", None],
        }
    )

    metrics = summarize_upload_metrics(uploads)

    assert metrics["missing_success_timings"] == 1
    assert metrics["mean_processing_ms"] is None
    assert metrics["std_processing_ms"] is None
    assert metrics["mean_page_count"] == 4.0


def test_empty_input_returns_safe_values() -> None:
    uploads = pd.DataFrame(
        columns=["status", "processing_ms", "page_count"]
    )

    metrics = summarize_upload_metrics(uploads)

    assert metrics["total_uploads"] == 0
    assert metrics["failure_rate_pct"] == 0.0
    assert metrics["mean_processing_ms"] is None


def test_missing_required_column_raises_error() -> None:
    uploads = pd.DataFrame({"status": ["success"]})

    with pytest.raises(ValueError, match="Missing columns"):
        summarize_upload_metrics(uploads)


def test_invalid_status_raises_error() -> None:
    uploads = pd.DataFrame(
        {
            "status": ["pending"],
            "processing_ms": [100],
            "page_count": [1],
        }
    )

    with pytest.raises(ValueError, match="status must"):
        summarize_upload_metrics(uploads)
