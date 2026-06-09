"""
Polarion deletion guardrails: build a deletion plan, show invalid links, require dual confirmation.

Agents must present the plan to the user, obtain **two separate** explicit approvals in chat,
then pass matching ``--confirm-token`` and ``--confirm-final`` to delete scripts (or
``confirmed=True`` on ``PolarionAdapter.delete_livedoc_module``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from .polarion_adapter import (
    PolarionAdapter,
    build_livedoc_portal_url,
    livedoc_module_location,
)

_MODULE_WORKITEM_MACRO_RE = re.compile(
    r"module-workitem;params=id=([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

LIVEDOC_CONFIRM_PREFIX = "DELETE-LIVEDOC:"
WORK_ITEMS_CONFIRM_PREFIX = "DELETE-WORK-ITEMS:"


@dataclass(frozen=True)
class WorkItemDeletionEntry:
    work_item_id: str
    title: str
    portal_url: str


@dataclass(frozen=True)
class LivedocDeletionPlan:
    project_id: str
    space_id: str
    module_name: str
    target_document: str
    livedoc_url: str
    module_title: str | None
    work_items: tuple[WorkItemDeletionEntry, ...] = ()
    module_exists: bool = True
    notes: tuple[str, ...] = ()

    @property
    def confirm_token(self) -> str:
        return f"{LIVEDOC_CONFIRM_PREFIX}{self.target_document}"


@dataclass(frozen=True)
class WorkItemsDeletionPlan:
    project_id: str
    work_items: tuple[WorkItemDeletionEntry, ...]
    notes: tuple[str, ...] = ()

    @property
    def confirm_token(self) -> str:
        ids = ",".join(sorted(e.work_item_id for e in self.work_items))
        return f"{WORK_ITEMS_CONFIRM_PREFIX}{ids}"


def work_item_portal_url(base_url: str, project_id: str, work_item_id: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/polarion/#/project/{project_id}/workitem?id={work_item_id}"


def _work_item_entry(
    adapter: PolarionAdapter, project_id: str, work_item_id: str
) -> WorkItemDeletionEntry:
    try:
        wi = adapter.get_work_item(work_item_id)
        title = wi.get("data", {}).get("attributes", {}).get("title") or "(no title)"
    except Exception:
        title = "(not found — may already be deleted)"
    return WorkItemDeletionEntry(
        work_item_id=work_item_id,
        title=title,
        portal_url=work_item_portal_url(adapter.base_url, project_id, work_item_id),
    )


def _work_items_from_livedoc_html(html_body: str) -> list[str]:
    return list(dict.fromkeys(_MODULE_WORKITEM_MACRO_RE.findall(html_body)))


def build_livedoc_deletion_plan(
    adapter: PolarionAdapter,
    space_id: str,
    module_name: str,
    *,
    project_id: str | None = None,
    extra_work_item_ids: Sequence[str] | None = None,
) -> LivedocDeletionPlan:
    """Inspect a LiveDoc module and list URLs that will stop working after deletion."""
    from polarion_rest_client.document import Document

    proj = project_id or adapter.project_id
    target = f"{proj}/{space_id}/{module_name}"
    livedoc_url = build_livedoc_portal_url(adapter.base_url, proj, space_id, module_name)
    module_title: str | None = None
    module_exists = True
    notes: list[str] = []
    wi_ids: list[str] = list(extra_work_item_ids or [])

    try:
        doc = Document(adapter.client).get(
            proj, space_id, module_name, fields_documents="title,homePageContent"
        )
        attrs = doc.get("data", {}).get("attributes", {})
        module_title = attrs.get("title")
        home = attrs.get("homePageContent")
        html = ""
        if isinstance(home, dict):
            html = str(home.get("value") or "")
        elif isinstance(home, str):
            html = home
        for wid in _work_items_from_livedoc_html(html):
            if wid not in wi_ids:
                wi_ids.append(wid)
    except Exception as exc:
        module_exists = False
        notes.append(f"LiveDoc module not found via REST ({exc}). SOAP delete may still apply.")
        notes.append(
            f"Location for SOAP lookup: {livedoc_module_location(space_id, module_name)}"
        )

    entries = tuple(_work_item_entry(adapter, proj, wid) for wid in wi_ids)
    if entries:
        notes.append(
            "Testcase work items listed above may become orphaned or be removed by Polarion "
            "when the module is deleted — confirm with the user whether to delete them separately."
        )
    else:
        notes.append("No testcase work items were discovered on the LiveDoc home page.")

    return LivedocDeletionPlan(
        project_id=proj,
        space_id=space_id,
        module_name=module_name,
        target_document=target,
        livedoc_url=livedoc_url,
        module_title=module_title,
        work_items=entries,
        module_exists=module_exists,
        notes=tuple(notes),
    )


def build_work_items_deletion_plan(
    adapter: PolarionAdapter,
    work_item_ids: Sequence[str],
    *,
    project_id: str | None = None,
) -> WorkItemsDeletionPlan:
    proj = project_id or adapter.project_id
    ids = [x.strip() for x in work_item_ids if x.strip()]
    if not ids:
        raise ValueError("At least one work item id is required for a deletion plan.")
    entries = tuple(_work_item_entry(adapter, proj, wid) for wid in ids)
    return WorkItemsDeletionPlan(project_id=proj, work_items=entries)


def require_dual_confirmation(
    confirm_token: str | None,
    confirm_final: str | None,
    expected_token: str,
) -> None:
    """
    Enforce two CLI confirmations that match the plan token.

    The agent must obtain **two separate** user approvals in chat before passing these flags.
    """
    if not confirm_token or not confirm_final:
        raise SystemExit(
            "Deletion refused: obtain double user confirmation in chat, then pass "
            f"--confirm-token and --confirm-final both set to {expected_token!r}."
        )
    if confirm_token != expected_token or confirm_final != expected_token:
        raise SystemExit(
            "Deletion refused: --confirm-token and --confirm-final must both match "
            f"the plan token {expected_token!r} exactly."
        )


def format_livedoc_deletion_plan_markdown(plan: LivedocDeletionPlan) -> str:
    lines = [
        "## Polarion LiveDoc deletion plan",
        "",
        f"- **REST target:** `{plan.target_document}`",
        f"- **Module title:** {plan.module_title or '(unknown)'}",
        f"- **Module exists (REST):** {'yes' if plan.module_exists else 'no'}",
        "",
        "### Link that will stop working",
        "",
        f"- LiveDoc wiki: {plan.livedoc_url}",
        "",
    ]
    if plan.work_items:
        lines.extend(
            [
                "### Testcase work items referenced on the LiveDoc (review before delete)",
                "",
            ]
        )
        for entry in plan.work_items:
            lines.append(f"- **{entry.work_item_id}** — {entry.title}")
            lines.append(f"  - {entry.portal_url}")
        lines.append("")
    if plan.notes:
        lines.append("### Notes")
        lines.append("")
        for note in plan.notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.extend(
        [
            "### Required user confirmations (agent — two separate chat turns)",
            "",
            "1. Show this plan and ask whether to proceed to **final** confirmation.",
            "2. After the user agrees once, show the **same** plan again and ask for explicit "
            f"final approval using the token: `{plan.confirm_token}`",
            "3. Only then run the delete script with `--confirm-token` and `--confirm-final` "
            "both set to that token.",
            "",
            f"**Confirm token:** `{plan.confirm_token}`",
        ]
    )
    return "\n".join(lines)


def format_work_items_deletion_plan_markdown(plan: WorkItemsDeletionPlan) -> str:
    lines = [
        "## Polarion work item deletion plan",
        "",
        f"- **Project:** {plan.project_id}",
        f"- **Count:** {len(plan.work_items)} work item(s)",
        "",
        "### Links that will stop working",
        "",
    ]
    for entry in plan.work_items:
        lines.append(f"- **{entry.work_item_id}** — {entry.title}")
        lines.append(f"  - {entry.portal_url}")
    lines.append("")
    if plan.notes:
        lines.append("### Notes")
        lines.append("")
        for note in plan.notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.extend(
        [
            "### Required user confirmations (agent — two separate chat turns)",
            "",
            "1. Show this plan and ask whether to proceed to **final** confirmation.",
            "2. After the user agrees once, show the **same** plan again and ask for explicit "
            f"final approval using the token: `{plan.confirm_token}`",
            "3. Only then run the delete script with `--confirm-token` and `--confirm-final` "
            "both set to that token.",
            "",
            f"**Confirm token:** `{plan.confirm_token}`",
        ]
    )
    return "\n".join(lines)
