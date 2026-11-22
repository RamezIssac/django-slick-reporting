#!/usr/bin/env python
"""Print a markdown report of the mutants on the lines a patch adds, read from mutmut's cache.

Usage: python scripts/mutation_report.py pr.patch
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter

from mutmut import read_patch_data

STATUS_BY_TAG = {"failure": "survived", "error": "timeout", "skipped": "untested"}


def mutant_status(case):
    return next((status for tag, status in STATUS_BY_TAG.items() if case.find(tag) is not None), "killed")


def main(patch_path):
    changed_lines = read_patch_data(patch_path)
    junit = subprocess.run(
        ["mutmut", "junitxml", "--untested-policy", "skipped"], capture_output=True, text=True, check=True
    ).stdout
    mutants = [
        case
        for case in ET.fromstring(junit).iter("testcase")
        if int(case.get("line")) in changed_lines.get(case.get("file"), ())
    ]
    counts = Counter(mutant_status(case) for case in mutants)

    print("## Mutation testing: lines changed by this PR\n")
    print("| Mutants | Killed | Survived | Timeout | Untested |")
    print("|---:|---:|---:|---:|---:|")
    print(
        f"| {len(mutants)} | {counts['killed']} | {counts['survived']} | {counts['timeout']} | {counts['untested']} |"
    )
    survivors = [case for case in mutants if mutant_status(case) == "survived"]
    if survivors:
        print("\n### Surviving mutants\n")
    for case in survivors:
        print(f"`{case.get('file')}:{case.get('line')}`\n\n```diff\n{case.find('failure').text.strip()}\n```\n")


if __name__ == "__main__":
    main(sys.argv[1])
