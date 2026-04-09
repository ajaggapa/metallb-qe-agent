#!/usr/bin/env python3
"""Validate required sections in a high-level test plan markdown file."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    r"^# High-Level Test Plan:\s+.+\(.+\)\s*$",
    r"^## JIRA Reference\s*$",
    r"^## Feature Summary\s*$",
    r"^## Scope\s*$",
    r"^### In Scope\s*$",
    r"^### Out of Scope / Limitations\s*$",
    r"^## Test Cases\s*$",
    r"^## References\s*$",
]


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    def has_heading(pattern: str) -> bool:
        rx = re.compile(pattern, re.MULTILINE)
        return bool(rx.search(content))

    for pattern in REQUIRED_HEADINGS:
        if not has_heading(pattern):
            errors.append(f"Missing required heading matching: {pattern}")

    tc_heading_rx = re.compile(r"^### TC-(\d{2}):\s+.+$", re.MULTILINE)
    tc_matches = list(tc_heading_rx.finditer(content))
    if len(tc_matches) < 3:
        errors.append("Expected at least 3 test cases (TC-01, TC-02, TC-03...).")
    else:
        required_tc_fields = [
            "**Purpose:**",
            "**Procedure:**",
            "**Expected Result:**",
            "**Pass/Fail Criteria:**",
        ]
        for idx, match in enumerate(tc_matches):
            block_start = match.start()
            block_end = tc_matches[idx + 1].start() if idx + 1 < len(tc_matches) else len(content)
            block = content[block_start:block_end]
            tc_label = f"TC-{match.group(1)}"
            for field in required_tc_fields:
                if field not in block:
                    errors.append(f"{tc_label} is missing field: {field}")

    if not any(line.startswith("- Ticket Key: `") for line in lines):
        errors.append("Missing Jira ticket key line under JIRA Reference.")
    if not any(line.startswith("- Ticket URL: ") for line in lines):
        errors.append("Missing Jira ticket URL line under JIRA Reference.")

    ref_lines = [line for line in lines if re.match(r"^\d+\.\s*\S+", line)]
    if len(ref_lines) < 1:
        errors.append("References section should include at least one populated reference entry.")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_test_plan.py <path-to-markdown>")
        return 2

    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        return 2

    content = path.read_text(encoding="utf-8")
    errors = validate(content)
    if errors:
        print("Validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
