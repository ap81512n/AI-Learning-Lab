<div align="center">

# FDE Learning Lab

Document-management and PDF question-answering API, with command-line utilities for document metadata and environment status.

</div>

## Requirements

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
- Docker Desktop is only needed for the optional Compose setup.
- OpenAI API credentials are only needed for PDF question answering; the API and other routes can start without them.

## Install and run locally

From the project root:

```sh
uv sync --dev
uv run uvicorn fde_learning_lab.api:app --reload
```

The API listens at <http://127.0.0.1:8000>. Check <http://127.0.0.1:8000/health> for health and open <http://127.0.0.1:8000/docs> for interactive API documentation. SQLite tables are initialized automatically at `data/documents.sqlite3` (override with `FDE_DB_PATH`); uploads default to `data/uploads` (override with `FDE_UPLOAD_DIR`).

## PDF Q&A configuration

Copy `.env.example` to `.env`, replace the OpenAI placeholders with valid values, then call `POST /ask`:

```sh
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
LLM_INPUT_USD_PER_1M=your_model_input_rate
LLM_OUTPUT_USD_PER_1M=your_model_output_rate
```

The rate values are used to estimate token costs and should match the selected model's current pricing. Upload a PDF using `POST /documents/upload`, then pass its returned `upload_id` and a question to `POST /ask`.

## CLI utilities

```sh
uv run fde-doc path/to/document.txt --pretty
uv run fde-learning-lab --client example-client --environment development
```

`fde-doc` prints JSON metadata (filename, character, word, and line counts); `--verbose` sends debug logs to stderr. The `fde-learning-lab` command prints a simple environment status.

## Tests

```sh
uv run pytest -v
```

## Optional Docker Compose

The API's `/app/data` directory is bind-mounted to the project’s `data/` directory, so uploaded PDFs appear under `data/uploads/`. Compose uses a local-only PostgreSQL password if none is set; override it in `.env` for development.

Run Compose with:

```sh
docker compose up --build
```

On Linux, set `LOCAL_UID` and `LOCAL_GID` to the values from `id -u` and `id -g` when starting Compose so the API can write to the bind-mounted directory. **The current API persists documents in SQLite, not PostgreSQL**, and Compose does not pass OpenAI settings into the API container, so PDF Q&A in Docker needs additional environment wiring.

## Project files

Each file below is described in one short line.

### Application (`src/fde_learning_lab/`)

| File | Purpose |
| --- | --- |
| `__init__.py` | Defines the environment-status CLI. |
| `api.py` | Creates the FastAPI app and document endpoints. |
| `ask_api.py` | Implements the PDF question-answering endpoint. |
| `db.py` | Defines SQLite tables and document persistence operations. |
| `document_cli.py` | Reads text files and prints JSON metadata. |
| `exceptions.py` | Defines application document exceptions. |
| `models.py` | Defines Pydantic document and ingestion models. |
| `upload_api.py` | Validates and stores PDF uploads. |
| `llm/__init__.py` | Package marker for language-model integration. |
| `llm/adapter.py` | Calls OpenAI and calculates usage/cost metadata. |
| `qa/__init__.py` | Package marker for PDF Q&A utilities. |
| `qa/document_qa.py` | Builds and validates answers from PDF page text. |
| `qa/pdf_pages.py` | Extracts page-numbered text from PDFs. |

### Tests (`tests/`)

| File | Purpose |
| --- | --- |
| `conftest.py` | Provides isolated API and upload fixtures. |
| `test_api.py` | Tests API health and document routes. |
| `test_api_isolation.py` | Tests upload limits, paths, and isolation. |
| `test_cli.py` | Tests the environment-status CLI. |
| `test_db.py` | Tests SQLite persistence and constraints. |
| `test_document_cli.py` | Tests document metadata CLI behavior. |
| `test_models.py` | Tests Pydantic validation rules. |
| `test_toke_sampling.py` | Tests token-sampling utilities. |
| `test_upload_api.py` | Tests PDF upload validation and storage. |

### Configuration and packaging

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Declares dependencies, package metadata, and CLI entry points. |
| `uv.lock` | Locks resolved dependency versions. |
| `Dockerfile` | Builds the API container image. |
| `compose.yaml` | Defines the API and PostgreSQL development services. |
| `.env.example` | Provides example local and Compose environment variables. |
| `.gitignore` | Excludes local environments, databases, and generated files. |
| `.dockerignore` | Excludes unnecessary files from Docker build context. |
