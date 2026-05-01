#!/usr/bin/env python
"""Extract a single version's section from CHANGELOG.md and print it to stdout.

Usage: python scripts/extract_changelog.py 1.4.0
"""
import re
import sys


def extract(version: str, changelog_path: str = "CHANGELOG.md") -> str:
    with open(changelog_path) as f:
        text = f.read()

    # Match the heading for the requested version (e.g. ## [1.4.0] or ## [1.4.0] - 2026-05-01)
    pattern = rf"(^## \[{re.escape(version)}\][^\n]*\n)(.*?)(?=^## \[|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        print(f"Version {version} not found in {changelog_path}", file=sys.stderr)
        sys.exit(1)

    # Return the body without the heading line itself
    return match.group(2).strip()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version>", file=sys.stderr)
        sys.exit(1)
    print(extract(sys.argv[1]))
