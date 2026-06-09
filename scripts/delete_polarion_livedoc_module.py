#!/usr/bin/env python3
"""
Delete a Polarion LiveDoc module via SOAP (REST document DELETE is not supported).

Default (no confirmation flags): print a deletion plan only — no changes.

Requires double user confirmation in chat before delete:
  --confirm-token and --confirm-final must both match the plan confirm token.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters.polarion_adapter import PolarionAdapter, read_qe_env  # noqa: E402
from adapters.polarion_deletion import (  # noqa: E402
    build_livedoc_deletion_plan,
    format_livedoc_deletion_plan_markdown,
    require_dual_confirmation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete a Polarion LiveDoc module (plan-only unless doubly confirmed)."
    )
    parser.add_argument("--space-id", required=True, help="Polarion space id (e.g. CNF)")
    parser.add_argument("--module-name", required=True, help="LiveDoc module name")
    parser.add_argument(
        "--project-id",
        default=None,
        help="Polarion project id (default: POLARION_PROJECT_ID from .env)",
    )
    parser.add_argument(
        "--work-items",
        default=None,
        metavar="IDS",
        help="Optional comma-separated testcase ids to list in the plan (in addition to LiveDoc macros)",
    )
    parser.add_argument(
        "--confirm-token",
        default=None,
        help="First confirmation token (must match plan; use only after user approves twice in chat)",
    )
    parser.add_argument(
        "--confirm-final",
        default=None,
        help="Second confirmation token (must equal --confirm-token)",
    )
    args = parser.parse_args(argv)

    env = read_qe_env(ROOT / ".env")
    base = env.get("POLARION_BASE_URL")
    proj = args.project_id or env.get("POLARION_PROJECT_ID")
    token = env.get("POLARION_TOKEN")
    if not all([base, proj, token]):
        print("Missing POLARION_BASE_URL, POLARION_PROJECT_ID, or POLARION_TOKEN", file=sys.stderr)
        return 2

    extra_ids = (
        [x.strip() for x in args.work_items.split(",") if x.strip()] if args.work_items else None
    )
    adapter = PolarionAdapter(base_url=base, project_id=proj, token=token)
    plan = build_livedoc_deletion_plan(
        adapter,
        args.space_id,
        args.module_name,
        project_id=proj,
        extra_work_item_ids=extra_ids,
    )
    print(format_livedoc_deletion_plan_markdown(plan))

    if not args.confirm_token and not args.confirm_final:
        print("\nPlan only — no deletion performed.", file=sys.stderr)
        return 0

    require_dual_confirmation(args.confirm_token, args.confirm_final, plan.confirm_token)
    adapter.delete_livedoc_module(
        args.space_id, args.module_name, project_id=proj, confirmed=True
    )
    print(f"\nDeleted LiveDoc module: {plan.target_document}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
