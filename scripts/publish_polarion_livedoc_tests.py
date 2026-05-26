#!/usr/bin/env python3
"""
Generic Polarion LiveDoc publisher: load testcase definitions from a Python epic module,
create testcase work items, optionally replace stale items, PATCH home page HTML.

Prerequisites:
  pip install polarion-rest-client
  .env: POLARION_BASE_URL, POLARION_PROJECT_ID, POLARION_TOKEN
  Optional: POLARION_SPACE_ID
  Optional traceability: POLARION_TRACE_* (highest), or METALLB_JIRA_EPIC_KEY + optional
    METALLB_HIGH_LEVEL_PLAN_URL / METALLB_DETAILED_PLAN_URL when POLARION_TRACE_* unset.
    Shell exports for POLARION_*, METALLB_*, JIRA_* override .env (see read_qe_env).

Usage:
  PYTHONPATH=examples python3 scripts/publish_polarion_livedoc_tests.py \\
    --epic-module polarion_livedoc_epic_module.sample_epic --dry-run

  # Or set POLARION_EPIC_MODULE=my_package.my_epic (import path on PYTHONPATH).

Epic module API (see examples/polarion_livedoc_epic_module/sample_epic.py):
  - default_traceability() -> dict  (required)
  - test_definitions(trace) -> list[dict]  (required; Polarion testcase shape)
  - DEFAULT_SPACE_ID, DEFAULT_MODULE_NAME, DEFAULT_DOCUMENT_TITLE, DEFAULT_LIVEDOC_H1_TITLE (optional)
  - REPLACE_STALE_WORK_ITEMS = (lucene_query, title_substring) or None for --replace-module-testcases
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters.polarion_adapter import PolarionAdapter, read_qe_env  # noqa: E402
from adapters.polarion_test_publish import (  # noqa: E402
    apply_traceability_cli,
    discover_work_item_ids_by_title_marker,
    merge_traceability_from_env,
    traceability_section_html,
)


def _load_epic(epic_module: str) -> ModuleType:
    try:
        return importlib.import_module(epic_module)
    except ImportError as e:
        raise SystemExit(f"Cannot import epic module {epic_module!r}: {e}") from e


def _get(mod: ModuleType, name: str, default: Any = None) -> Any:
    return getattr(mod, name, default)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish Polarion testcase LiveDoc from an epic Python module."
    )
    parser.add_argument(
        "--epic-module",
        default=None,
        help="Import path (e.g. polarion_livedoc_epic_module.sample_epic). Default: env POLARION_EPIC_MODULE.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions only.")
    parser.add_argument(
        "--space-id",
        default=None,
        help="Polarion space id (default: epic DEFAULT_SPACE_ID or env POLARION_SPACE_ID or CNF).",
    )
    parser.add_argument(
        "--module-name",
        default=None,
        help="LiveDoc module name (default: epic DEFAULT_MODULE_NAME).",
    )
    parser.add_argument(
        "--document-title",
        default=None,
        help="Title when creating LiveDoc (default: epic DEFAULT_DOCUMENT_TITLE).",
    )
    parser.add_argument(
        "--livedoc-h1-title",
        default=None,
        help="H1 on home page HTML (default: epic DEFAULT_LIVEDOC_H1_TITLE or document title).",
    )
    parser.add_argument(
        "--delete-work-items",
        default=None,
        metavar="IDS",
        help="Comma-separated work item ids to delete before publishing.",
    )
    parser.add_argument(
        "--skip-document-create",
        action="store_true",
        help="Do not POST a new LiveDoc; attach to existing module.",
    )
    parser.add_argument(
        "--home-page-only",
        action="store_true",
        help="Only PATCH home page (requires --attach-work-items).",
    )
    parser.add_argument(
        "--attach-work-items",
        default=None,
        metavar="IDS",
        help="Comma-separated work item ids in testcase order (for --home-page-only).",
    )
    parser.add_argument(
        "--resync-steps-and-home",
        action="store_true",
        help="With --home-page-only: replace Test Steps + PATCH home.",
    )
    parser.add_argument(
        "--document-project-id",
        default=None,
        help="Polarion project for LiveDoc + work items (default: POLARION_PROJECT_ID).",
    )
    parser.add_argument(
        "--replace-module-testcases",
        action="store_true",
        help="Delete stale WIs (see epic REPLACE_STALE_WORK_ITEMS or CLI query/substring), "
        "then create testcases (implies --skip-document-create).",
    )
    parser.add_argument(
        "--replace-lucene-query",
        default=None,
        help="With --replace-module-testcases if epic defines no REPLACE_STALE_WORK_ITEMS: Lucene query.",
    )
    parser.add_argument(
        "--replace-title-substring",
        default=None,
        help="With --replace-module-testcases: title must contain this substring.",
    )
    parser.add_argument("--epic-url", default=None, help="Override traceability epic URL.")
    parser.add_argument("--epic-label", default=None, help="Override traceability epic label text.")
    parser.add_argument("--high-level-plan-url", default=None, help="Override high-level plan URL.")
    parser.add_argument("--detailed-plan-url", default=None, help="Override detailed plan URL.")

    args = parser.parse_args(argv)

    epic_name = args.epic_module or os.environ.get("POLARION_EPIC_MODULE", "").strip()
    if not epic_name:
        print(
            "Provide --epic-module <import.path.to.epic> or set POLARION_EPIC_MODULE "
            "(module must be importable, e.g. PYTHONPATH=examples for the sample).",
            file=sys.stderr,
        )
        return 2

    if args.replace_module_testcases:
        args.skip_document_create = True

    env_file = ROOT / ".env"
    env = read_qe_env(env_file)
    base = env.get("POLARION_BASE_URL")
    proj = env.get("POLARION_PROJECT_ID")
    token = env.get("POLARION_TOKEN")
    doc_project = args.document_project_id or proj

    if not all([base, proj, token]):
        print(
            "Missing POLARION_BASE_URL, POLARION_PROJECT_ID, or POLARION_TOKEN in .env",
            file=sys.stderr,
        )
        return 2
    if not doc_project:
        print("No document project id.", file=sys.stderr)
        return 2

    mod = _load_epic(epic_name)

    if not callable(_get(mod, "default_traceability")) or not callable(
        _get(mod, "test_definitions")
    ):
        print(
            f"Epic module {epic_name!r} must define default_traceability() and test_definitions(trace).",
            file=sys.stderr,
        )
        return 2

    space = (
        args.space_id
        or _get(mod, "DEFAULT_SPACE_ID")
        or env.get("POLARION_SPACE_ID")
        or "CNF"
    )
    module_name = args.module_name or _get(mod, "DEFAULT_MODULE_NAME")
    if not module_name:
        print("Set DEFAULT_MODULE_NAME on the epic module or pass --module-name.", file=sys.stderr)
        return 2

    title_doc = args.document_title or _get(mod, "DEFAULT_DOCUMENT_TITLE")
    if not title_doc:
        print(
            "Set DEFAULT_DOCUMENT_TITLE on the epic module or pass --document-title.",
            file=sys.stderr,
        )
        return 2

    livedoc_h1 = args.livedoc_h1_title or _get(
        mod, "DEFAULT_LIVEDOC_H1_TITLE", title_doc
    )

    target_document = f"{doc_project}/{space}/{module_name}"
    trace = apply_traceability_cli(
        merge_traceability_from_env(mod.default_traceability(), env), args
    )
    tests = mod.test_definitions(trace)

    stale_cfg = _get(mod, "REPLACE_STALE_WORK_ITEMS")
    lucene_q = args.replace_lucene_query
    title_sub = args.replace_title_substring
    if args.replace_module_testcases:
        if stale_cfg and len(stale_cfg) == 2:
            lucene_q, title_sub = stale_cfg[0], stale_cfg[1]
        if not lucene_q or not title_sub:
            print(
                "For --replace-module-testcases define REPLACE_STALE_WORK_ITEMS on the epic module "
                "or pass --replace-lucene-query and --replace-title-substring.",
                file=sys.stderr,
            )
            return 2

    if args.dry_run:
        print("Dry run — would create:")
        print(f"  Epic module: {epic_name}")
        print(f"  Document project: {doc_project}")
        print(f"  Target module: {target_document}")
        print(f"  Traceability epic: {trace['epic_label']} -> {trace['epic_url']}")
        print(f"  High-level plan URL: {trace['high_level_plan_url']}")
        print(f"  Detailed plan URL: {trace['detailed_plan_url']}")
        if args.replace_module_testcases:
            print(
                f"  Replace stale WIs: query={lucene_q!r} substring={title_sub!r}"
            )
        if args.delete_work_items:
            print(f"  Delete work items: {args.delete_work_items}")
        if args.home_page_only:
            print("  Home page only")
            if args.attach_work_items:
                print(f"  Work items: {args.attach_work_items}")
        if not args.skip_document_create and not args.home_page_only:
            print(f"  Create LiveDoc title: {title_doc}")
        elif args.skip_document_create and not args.home_page_only:
            print(f"  Skip document create; target: {target_document}")
        for t in tests:
            print(f"  - {t['title']} ({len(t['steps'])} steps)")
        if not args.home_page_only:
            print("  Then: PATCH LiveDoc home page.")
        return 0

    adapter = PolarionAdapter(base_url=base, project_id=doc_project, token=token)

    if args.home_page_only:
        if not args.attach_work_items:
            print("--home-page-only requires --attach-work-items", file=sys.stderr)
            return 2
        ids = [x.strip() for x in args.attach_work_items.split(",") if x.strip()]
        if len(ids) != len(tests):
            print(
                f"Expected {len(tests)} work item ids (testcase order), got {len(ids)}",
                file=sys.stderr,
            )
            return 2
        if args.resync_steps_and_home:
            for tc, wid in zip(tests, ids, strict=True):
                print(f"Replacing Polarion Test Steps for {wid} …")
                adapter.replace_test_steps(wid, tc["steps"])
        adapter.publish_livedoc_home_page(
            space,
            module_name,
            document_h1_title=livedoc_h1,
            traceability_html=traceability_section_html(trace),
            tests=tests,
            work_item_ids=ids,
        )
        print("Updated LiveDoc home page:", target_document)
        return 0

    if args.replace_module_testcases:
        stale = discover_work_item_ids_by_title_marker(
            adapter,
            doc_project,
            lucene_query=lucene_q,
            title_substring=title_sub,
        )
        if stale:
            print(f"Deleting {len(stale)} stale work items: {', '.join(stale)}")
            adapter.delete_work_items(stale)
        else:
            print("No matching stale work items found to delete.")

    if args.delete_work_items:
        to_del = [x.strip() for x in args.delete_work_items.split(",") if x.strip()]
        if to_del:
            print("Deleting work items:", ", ".join(to_del))
            adapter.delete_work_items(to_del)

    if args.skip_document_create:
        print("Skipping document create; using existing module:", target_document)
    else:
        doc = adapter.create_module_document(space, module_name, title=title_doc)
        print("Created document:", doc.get("id", doc))

    created_ids: list[str] = []
    for tc in tests:
        wid = adapter.create_testcase(
            title=tc["title"],
            description_html=tc["description_html"],
            setup_html=tc["setup_html"],
            teardown_html=tc["teardown_html"],
            status="draft",
        )
        adapter.add_test_steps(wid, tc["steps"])
        adapter.move_workitem_to_document(wid, target_document=target_document)
        portal = f"{base.rstrip('/')}/polarion/redirect/project/{doc_project}/workitem?id={wid}"
        print(f"Created & attached {wid}: {tc['title']}")
        print(f"  {portal}")
        created_ids.append(wid)

    adapter.publish_livedoc_home_page(
        space,
        module_name,
        document_h1_title=livedoc_h1,
        traceability_html=traceability_section_html(trace),
        tests=tests,
        work_item_ids=created_ids,
    )
    print("\nUpdated LiveDoc home page with embedded descriptions and test-step tables.")
    print("\nDone.")
    print(f"Document module: {target_document}")
    print(f"Test case IDs: {', '.join(created_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
