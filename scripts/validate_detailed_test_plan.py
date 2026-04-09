#!/usr/bin/env python3
"""Validate structure of a detailed MetalLB test plan markdown file."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    r"^# Detailed Test Plan:\s+.+\(.+\)\s*$",
    r"^## JIRA Reference\s*$",
    r"^## Related High-Level Test Plan\s*$",
    r"^## Prerequisites and Environment\s*$",
    r"^## Placeholders\s*$",
    r"^## Detailed Test Cases\s*$",
    r"^## References\s*$",
]

TC_HEADING = re.compile(r"^### (TC-\d{2}):\s+.+$", re.MULTILINE)
YAML_FENCE = re.compile(r"```(?:yaml|yml)\s*\n[\s\S]*?```", re.IGNORECASE)
SHELL_FENCE = re.compile(r"```(?:bash|sh|shell)\s*\n([\s\S]*?)```", re.IGNORECASE)
STEP_HEADING = re.compile(r"^#### Step\s+\d+", re.MULTILINE)


def _section_between(content: str, start_heading: str, end_heading: str | None) -> str:
    start_rx = re.compile(rf"^{re.escape(start_heading)}\s*$", re.MULTILINE)
    m = start_rx.search(content)
    if not m:
        return ""
    start = m.end()
    if end_heading:
        end_rx = re.compile(rf"^{re.escape(end_heading)}\s*$", re.MULTILINE)
        m2 = end_rx.search(content, pos=start)
        end = m2.start() if m2 else len(content)
    else:
        end = len(content)
    return content[start:end]


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    def has_heading(pattern: str) -> bool:
        return bool(re.compile(pattern, re.MULTILINE).search(content))

    for pattern in REQUIRED_HEADINGS:
        if not has_heading(pattern):
            errors.append(f"Missing required heading matching: {pattern}")

    if not any(line.startswith("- Ticket Key: `") for line in lines):
        errors.append("Missing Jira ticket key line under JIRA Reference (- Ticket Key: `...`).")
    if not any(line.startswith("- Ticket URL: ") for line in lines):
        errors.append("Missing Jira ticket URL line under JIRA Reference (- Ticket URL: ...).")

    related = _section_between(content, "## Related High-Level Test Plan", "## Prerequisites and Environment")
    if related.strip() and not re.search(r"^\s*-\s+\S", related, re.MULTILINE):
        errors.append("Related High-Level Test Plan should include at least one bullet (- ...).")

    placeholders = _section_between(content, "## Placeholders", "## Detailed Test Cases")
    if len(placeholders.strip()) < 3:
        errors.append("Placeholders section appears empty; add grouped bullet lists (avoid pipe tables for Google Docs readability).")

    tc_matches = list(TC_HEADING.finditer(content))
    if len(tc_matches) < 3:
        errors.append("Expected at least 3 detailed test cases (### TC-01, TC-02, ...).")
    else:
        for idx, match in enumerate(tc_matches):
            block_start = match.start()
            block_end = tc_matches[idx + 1].start() if idx + 1 < len(tc_matches) else len(content)
            block = content[block_start:block_end]
            label = match.group(1)
            if "**Purpose:**" not in block:
                errors.append(f"{label} is missing **Purpose:**")
            if "Pass/Fail" not in block:
                errors.append(f"{label} must mention Pass/Fail criteria (e.g. **Pass/Fail criteria (summary):**).")
            if not STEP_HEADING.search(block):
                errors.append(f"{label} should include at least one #### Step N heading.")
            if not YAML_FENCE.search(block):
                errors.append(f"{label} must include at least one ```yaml (or ```yml) fenced block.")
            shell_bodies = SHELL_FENCE.findall(block)
            if not shell_bodies:
                errors.append(
                    f"{label} must include at least one ```bash, ```sh, or ```shell fenced block."
                )
            elif not any(
                "oc " in b or "kubectl " in b or b.strip().startswith("oc") or b.strip().startswith("kubectl")
                for b in shell_bodies
            ):
                errors.append(
                    f"{label} shell fences must include oc or kubectl commands (e.g. `oc apply`, `kubectl get`)."
                )

    ref_section = _section_between(content, "## References", None)
    ref_lines = [ln for ln in ref_section.splitlines() if re.match(r"^\d+\.\s*\S+", ln.strip())]
    if len(ref_lines) < 1:
        errors.append("References section should include at least one numbered entry (1. ...).")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_detailed_test_plan.py <path-to-markdown>")
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
