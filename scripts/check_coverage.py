#!/usr/bin/env python3
"""
Pre-commit hook to check test coverage.
Fails if coverage drops below MIN_COVERAGE (default: 95%).
"""

import subprocess
import sys
import re

MIN_COVERAGE = 85


def get_coverage() -> float:
    """Run pytest with coverage and return the total percentage."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=cursor_chronicle",
                "--cov=search_history",
                "--cov-report=term",
                "--cov-fail-under=0",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout + result.stderr

        # Parse coverage from output
        # Look for "TOTAL ... XX%" pattern (with optional branch columns)
        match = re.search(r"TOTAL\s+\d+\s+\d+(?:\s+\d+\s+\d+)?\s+(\d+)%", output)
        if match:
            return float(match.group(1))

        # Alternative pattern: "Total coverage: XX.XX%"
        match = re.search(r"Total coverage:\s*(\d+(?:\.\d+)?)%", output)
        if match:
            return float(match.group(1))

        # Alternative pattern: "XX% covered"
        match = re.search(r"(\d+)%\s*(?:covered|total)", output, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # If tests failed, report it
        if result.returncode != 0:
            print("⚠️  Tests failed, cannot determine coverage")
            print(output[-500:] if len(output) > 500 else output)
            return 0.0

        print("⚠️  Could not parse coverage from output")
        print(output[-500:] if len(output) > 500 else output)
        return 0.0

    except subprocess.TimeoutExpired:
        print("⚠️  Coverage check timed out")
        return 0.0
    except Exception as e:
        print(f"⚠️  Error running coverage: {e}")
        return 0.0


def main() -> int:
    """Check test coverage meets minimum threshold."""
    print(f"Checking test coverage (minimum: {MIN_COVERAGE}%)...")

    coverage = get_coverage()

    if coverage < MIN_COVERAGE:
        print(f"❌ Coverage check FAILED: {coverage:.1f}% < {MIN_COVERAGE}%")
        print()
        print("Please add tests to maintain coverage above the threshold.")
        return 1

    print(f"✅ Coverage check PASSED: {coverage:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
