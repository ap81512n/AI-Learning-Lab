
#!/usr/bin/env bash
set -euo pipefail

# Locate the repository root.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Load trusted local configuration if present.
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

# Set defaults.
FDE_ENTRYPOINT="${FDE_ENTRYPOINT:-scripts/run_async_fetch.py}"
FDE_ENV="${FDE_ENV:-development}"

# Validate prerequisites.
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed or not on PATH." >&2
    exit 1
fi

if [[ ! -f "$FDE_ENTRYPOINT" ]]; then
    echo "Error: entrypoint not found: $FDE_ENTRYPOINT" >&2
    exit 1
fi

echo "Environment: $FDE_ENV"
echo "Starting: $FDE_ENTRYPOINT"

# Run using the project's uv environment.
uv run python "$FDE_ENTRYPOINT"
