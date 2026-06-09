#!/usr/bin/env python3
"""
Delete Polarion testcase work items.

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
    build_work_items_deletion_plan,
    format_work_items_deletion_plan_markdown,
    require_dual_confirmation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete Polarion work items (plan-only unless doubly confirmed)."
    )
    parser.add_argument(
        "--work-items",
        required=True,
        metavar="IDS",
        help="Comma-separated work item ids (e.g. OCP-89305,OCP-89306)",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="Polarion project id (default: POLARION_PROJECT_ID from .env)",
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

    ids = [x.strip() for x in args.work_items.split(",") if x.strip()]
    adapter = PolarionAdapter(base_url=base, project_id=proj, token=token)
    plan = build_work_items_deletion_plan(adapter, ids, project_id=proj)
    print(format_work_items_deletion_plan_markdown(plan))

    if not args.confirm_token and not args.confirm_final:
        print("\nPlan only — no deletion performed.", file=sys.stderr)
        return 0

    require_dual_confirmation(args.confirm_token, args.confirm_final, plan.confirm_token)
    adapter.delete_work_items([e.work_item_id for e in plan.work_items])
    print(f"\nDeleted {len(plan.work_items)} work item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
