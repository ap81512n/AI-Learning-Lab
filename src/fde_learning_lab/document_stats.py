
"""Descriptive statistics for document upload events."""

import pandas as pd


REQUIRED_COLUMNS = {"status", "processing_ms", "page_count"}
VALID_STATUSES = {"success", "failed"}


def summarize_upload_metrics(
    frame: pd.DataFrame,
) -> dict[str, int | float | None]:
    """Calculate statistics from document upload records."""

    missing = REQUIRED_COLUMNS - set(frame.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {', '.join(sorted(missing))}"
        )

    # Avoid modifying the original DataFrame.
    data = frame.copy()

    if not data["status"].isin(VALID_STATUSES).all():
        raise ValueError("status must be 'success' or 'failed'")

    # Convert numeric strings to numbers.
    # Invalid values become NaN.
    data["processing_ms"] = pd.to_numeric(
        data["processing_ms"], errors="coerce"
    )
    data["page_count"] = pd.to_numeric(
        data["page_count"], errors="coerce"
    )

    # Calculate timing statistics for successful uploads only.
    successful = data.loc[data["status"] == "success"]
    times = successful["processing_ms"].dropna()
    pages = successful["page_count"].dropna()

    total = len(data)
    failed = int((data["status"] == "failed").sum())

    return {
        "total_uploads": total,
        "successful_uploads": len(successful),
        "failed_uploads": failed,
        "failure_rate_pct": (
            round(failed / total * 100, 2) if total else 0.0
        ),
        "missing_success_timings": int(
            successful["processing_ms"].isna().sum()
        ),
        "mean_processing_ms": (
            float(times.mean()) if not times.empty else None
        ),
        "median_processing_ms": (
            float(times.median()) if not times.empty else None
        ),
        "variance_processing_ms2": (
            float(times.var(ddof=1)) if len(times) >= 2 else None
        ),
        "std_processing_ms": (
            float(times.std(ddof=1)) if len(times) >= 2 else None
        ),
        "p95_processing_ms": (
            float(times.quantile(0.95))
            if not times.empty else None
        ),
        "mean_page_count": (
            float(pages.mean()) if not pages.empty else None
        ),
    }
