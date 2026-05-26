# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for publishing Polarion testcase LiveDocs (traceability HTML, stale WI discovery).

Epic-specific defaults and ``test_definitions`` live in a Python module (any import path on ``PYTHONPATH``)
loaded by ``scripts/publish_polarion_livedoc_tests.py`` (see ``examples/polarion_livedoc_epic_module/sample_epic.py``).
"""

from __future__ import annotations

import html
from typing import Any, Mapping

from adapters.polarion_adapter import PolarionAdapter, html_paragraph

# Optional .env overrides (same for every epic)
_TRACE_ENV = (
    ("POLARION_TRACE_EPIC_URL", "epic_url"),
    ("POLARION_TRACE_EPIC_LABEL", "epic_label"),
    ("POLARION_TRACE_HIGH_LEVEL_PLAN_URL", "high_level_plan_url"),
    ("POLARION_TRACE_DETAILED_PLAN_URL", "detailed_plan_url"),
)


def merge_traceability_from_env(
    base: Mapping[str, str], env: Mapping[str, str]
) -> dict[str, str]:
    """
    Overlay traceability onto ``base`` (from epic module ``default_traceability()``).

    Precedence for each field:

    1. ``POLARION_TRACE_*`` in the merged env (highest).
    2. ``METALLB_*`` convenience keys when the corresponding ``POLARION_TRACE_*`` was **not** set.
    3. Values already in ``base`` (from the epic module).

    ``METALLB_JIRA_EPIC_KEY`` sets ``epic_label`` and, unless ``POLARION_TRACE_EPIC_URL`` is set,
    ``epic_url`` as ``{METALLB_JIRA_BROWSE_URL_BASE}/{key}`` (default browse base is Red Hat issues).
    """
    out = dict(base)
    for env_key, trace_key in _TRACE_ENV:
        v = env.get(env_key, "").strip()
        if v:
            out[trace_key] = v

    epic_key = env.get("METALLB_JIRA_EPIC_KEY", "").strip()
    browse_base = env.get("METALLB_JIRA_BROWSE_URL_BASE", "https://issues.redhat.com/browse").rstrip("/")
    if epic_key:
        if not env.get("POLARION_TRACE_EPIC_LABEL", "").strip():
            out["epic_label"] = epic_key
        if not env.get("POLARION_TRACE_EPIC_URL", "").strip():
            out["epic_url"] = f"{browse_base}/{epic_key}"

    hl = env.get("METALLB_HIGH_LEVEL_PLAN_URL", "").strip()
    if hl and not env.get("POLARION_TRACE_HIGH_LEVEL_PLAN_URL", "").strip():
        out["high_level_plan_url"] = hl

    dl = env.get("METALLB_DETAILED_PLAN_URL", "").strip()
    if dl and not env.get("POLARION_TRACE_DETAILED_PLAN_URL", "").strip():
        out["detailed_plan_url"] = dl

    return out


def apply_traceability_cli(trace: dict[str, str], args: Any) -> dict[str, str]:
    """Argparse overrides for traceability fields when attributes are set."""
    out = dict(trace)
    if getattr(args, "epic_url", None):
        out["epic_url"] = args.epic_url.strip()
    if getattr(args, "epic_label", None):
        out["epic_label"] = args.epic_label.strip()
    if getattr(args, "high_level_plan_url", None):
        out["high_level_plan_url"] = args.high_level_plan_url.strip()
    if getattr(args, "detailed_plan_url", None):
        out["detailed_plan_url"] = args.detailed_plan_url.strip()
    return out


def traceability_ul(trace: Mapping[str, str]) -> str:
    return (
        "<ul>"
        f'<li>Epic: <a href="{html.escape(trace["epic_url"], quote=True)}">'
        f'{html.escape(trace["epic_label"])}</a></li>'
        f'<li>High-level test plan: <a href="{html.escape(trace["high_level_plan_url"], quote=True)}">'
        "Google Doc</a></li>"
        f'<li>Detailed test plan: <a href="{html.escape(trace["detailed_plan_url"], quote=True)}">'
        "Google Doc</a></li>"
        "</ul>"
    )


def testcase_description_html(trace: Mapping[str, str], purpose: str, pass_fail: str) -> str:
    return (
        "<h4>Traceability</h4>"
        f"{traceability_ul(trace)}"
        "<h4>Purpose</h4>"
        f"{html_paragraph(purpose)}"
        "<h4>Pass / fail (summary)</h4>"
        f"{html_paragraph(pass_fail)}"
    )


def traceability_section_html(trace: Mapping[str, str]) -> str:
    return "<p><strong>Traceability</strong></p>" + traceability_ul(trace)


def discover_work_item_ids_by_title_marker(
    adapter: PolarionAdapter,
    project_id: str,
    *,
    lucene_query: str,
    title_substring: str,
    max_pages: int = 50,
) -> list[str]:
    """
    List work item short ids where Polarion search returns items matching ``lucene_query``
    and title contains ``title_substring``.
    """
    from polarion_rest_client.workitem import WorkItem

    wi = WorkItem(adapter.client)
    found: list[str] = []
    for page in range(1, max_pages + 1):
        items = wi.list(
            project_id,
            page_size=100,
            page_number=page,
            query=lucene_query,
            fields=["id", "title"],
        )
        if not items:
            break
        for it in items:
            title = (it.get("attributes") or {}).get("title") or ""
            if title_substring not in title:
                continue
            full_id = it.get("id") or ""
            short = full_id.split("/")[-1] if "/" in full_id else full_id
            if short:
                found.append(short)
        if len(items) < 100:
            break
    return sorted(set(found))
