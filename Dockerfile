
FROM python:3.12-slim

# Copy a pinned version of uv
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    FDE_DB_PATH=/app/data/documents.sqlite3 \
    FDE_UPLOAD_DIR=/app/data/uploads

# Install dependencies separately for Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Copy application files and finish installation
COPY . .
RUN uv sync --locked --no-dev

# Create writable directories and a non-root user
RUN useradd --uid 10001 --create-home appuser \
    && mkdir -p /app/data/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "fde_learning_lab.api:app", "--host", "0.0.0.0", "--port", "8000"]
