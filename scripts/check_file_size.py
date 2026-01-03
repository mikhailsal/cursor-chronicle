#!/usr/bin/env python3
"""
Pre-commit hook to check Python file sizes.
Fails if any file exceeds MAX_LINES (default: 400 lines).
"""

import sys
from pathlib import Path

MAX_LINES = 400


def count_lines(file_path: str) -> int:
    """Count non-empty lines in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except (IOError, UnicodeDecodeError):
        return 0


def main() -> int:
    """Check file sizes for all provided files."""
    files = sys.argv[1:]

    if not files:
        return 0

    violations = []

    for file_path in files:
        path = Path(file_path)

        # Skip non-Python files
        if path.suffix != ".py":
            continue

        # Skip __init__.py files (often just exports)
        if path.name == "__init__.py":
            continue

        # Skip test configuration files
        if path.name == "conftest.py":
            continue

        line_count = count_lines(file_path)

        if line_count > MAX_LINES:
            violations.append((file_path, line_count))

    if violations:
        print(f"❌ File size check FAILED (max {MAX_LINES} lines)")
        print("-" * 50)
        for file_path, line_count in violations:
            over = line_count - MAX_LINES
            print(f"  {file_path}: {line_count} lines (+{over} over limit)")
        print()
        print("Please split large files into smaller modules.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
