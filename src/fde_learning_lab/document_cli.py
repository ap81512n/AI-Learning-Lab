"""Command-line interface for inspecting local text documents."""

import argparse
import json
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def build_metadata(
    filename: str,
    content: str,
) -> dict[str, str | int]:
    """Return JSON-compatible metadata for a text document."""
    return {
        "filename": filename,
        "characters": len(content),
        "words": len(content.split()),
        "lines": len(content.splitlines()),
    }


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and print metadata. Return an exit code."""

    parser = argparse.ArgumentParser(description="Inspect a local UTF-8 text document")

    parser.add_argument(
        "path",
        type=Path,
        help="Path to a UTF-8 text file",
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent JSON output",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log diagnostic details",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        content = args.path.read_text(encoding="utf-8")

    except (OSError, UnicodeError) as exc:
        LOGGER.error(
            "Cannot read file '%s': %s",
            args.path,
            exc,
        )
        return 2

    LOGGER.debug(
        "Loaded %s (%d characters)",
        args.path.name,
        len(content),
    )

    metadata = build_metadata(args.path.name, content)

    print(
        json.dumps(
            metadata,
            indent=2 if args.pretty else None,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
