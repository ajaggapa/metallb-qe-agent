"""
Reusable Polarion LiveDoc home-page HTML for testcase collections.

Polarion only shows testcase *titles* in the outline if the home page is only work-item macros.
Always PATCH `homePageContent` with readable content; link each WI from its section (no trailing macro list).

See `.cursor/rules/metallb-polarion-livedoc-workflow.mdc` and skill `metallb-polarion-test-publish`.
"""

from __future__ import annotations

import html
from typing import Any, Sequence

# LiveDoc home pages must not end with a "Linked Polarion test cases" block or
# `module-workitem` wiki macros—each testcase links to its WI under its heading.
_FORBIDDEN_MACRO_MARKER = "module-workitem"
_FORBIDDEN_SECTION_TITLE = "linked polarion test cases"


def validate_livedoc_home_html_policy(html_body: str) -> None:
    """
    Ensure home-page HTML matches project policy (no macro footer, no linked-WI section).

    Called automatically by ``build_livedoc_home_html`` before returning. Call this if you
    assemble equivalent HTML elsewhere before ``PolarionAdapter.update_document_home_page``.

    Raises:
        ValueError: if forbidden Polarion macro markers or the deprecated section title appear.
    """
    lower = html_body.casefold()
    if _FORBIDDEN_MACRO_MARKER.casefold() in lower:
        raise ValueError(
            f"LiveDoc home HTML must not contain {_FORBIDDEN_MACRO_MARKER!r} (Polarion wiki "
            "macro). Use per-testcase portal links from build_livedoc_home_html only."
        )
    if _FORBIDDEN_SECTION_TITLE in lower:
        raise ValueError(
            'LiveDoc home HTML must not contain a "Linked Polarion test cases" section '
            "(use the Polarion work item link under each testcase title only)."
        )


def build_livedoc_home_html(
    *,
    document_h1_title: str,
    traceability_html: str,
    tests: list[dict[str, Any]],
    project_id: str,
    base_url: str,
    work_item_ids: Sequence[str],
) -> str:
    """
    Build full HTML for a LiveDoc module home page.

    Each entry in ``tests`` should provide:
      - title: str
      - description_html: str (already HTML)
      - setup_html: str
      - teardown_html: str
      - steps: list[tuple[str, str]]  (Step column, Expected Result) plain text

    ``work_item_ids`` must be in the same order as ``tests`` (short ids, e.g. OCP-12345).

    Polarion constraints encoded here:
      - Leading ``<p id="polarion_1"></p>`` (do not add custom id= on headings; PATCH may fail).
      - Subsections use bold ``<p>`` blocks, not ``<h3>`` (Polarion may rewrite h3 into empty macros).
      - Work items are linked from each testcase heading (portal URL only); no trailing
        "Linked Polarion test cases" section or ``module-workitem`` macros (enforced by
        ``validate_livedoc_home_html_policy`` before return).
    """
    base = base_url.rstrip("/")
    ids = list(work_item_ids)
    if len(ids) != len(tests):
        raise ValueError(
            f"work_item_ids length ({len(ids)}) must match tests length ({len(tests)})"
        )

    chunks: list[str] = []

    chunks.append('<p id="polarion_1"></p>')
    chunks.append(f"<h1>{html.escape(document_h1_title)}</h1>")
    chunks.append(traceability_html)

    chunks.append("<h2>Contents</h2><ul>")
    for tc in tests:
        chunks.append(f"<li>{html.escape(tc['title'])}</li>")
    chunks.append("</ul>")

    for tc, wid in zip(tests, ids, strict=True):
        portal = f"{base}/polarion/redirect/project/{project_id}/workitem?id={wid}"
        chunks.append(f"<h2>{html.escape(tc['title'])}</h2>")
        chunks.append(
            "<p><strong>Polarion test case:</strong> "
            f'<a href="{html.escape(portal, quote=True)}">{html.escape(wid)}</a></p>'
        )

        chunks.append(
            '<p style="margin-top:1.2em;margin-bottom:0.4em;">'
            "<strong>Description</strong></p>"
        )
        chunks.append(tc["description_html"])

        chunks.append(
            '<p style="margin-top:1em;margin-bottom:0.4em;"><strong>Setup</strong></p>'
        )
        chunks.append(tc["setup_html"])

        chunks.append(
            '<p style="margin-top:1em;margin-bottom:0.4em;"><strong>Test steps</strong></p>'
        )
        # table-layout:fixed + 50% columns so cells get a bounded width; pre-wrap + break-word for wrapping
        chunks.append(
            '<table border="1" cellpadding="6" cellspacing="0" '
            'style="border-collapse:collapse;width:100%;table-layout:fixed;">'
        )
        chunks.append(
            "<thead><tr>"
            "<th scope=\"col\" style=\"text-align:left;width:50%;\">Step</th>"
            "<th scope=\"col\" style=\"text-align:left;width:50%;\">Expected Result</th>"
            "</tr></thead><tbody>"
        )
        _cell = (
            '<div style="'
            "white-space:pre-wrap;"
            "overflow-wrap:break-word;"
            "word-wrap:break-word;"
            "word-break:break-word;"
            "font-family:monospace,monospace;"
            "font-size:12px;"
            "line-height:1.4;"
            "margin:0;"
            '">{}</div>'
        )
        for step_text, exp_text in tc["steps"]:
            chunks.append("<tr>")
            chunks.append(
                '<td style="vertical-align:top;width:50%;">'
                + _cell.format(html.escape(step_text))
                + "</td>"
            )
            chunks.append(
                '<td style="vertical-align:top;width:50%;">'
                + _cell.format(html.escape(exp_text))
                + "</td>"
            )
            chunks.append("</tr>")
        chunks.append("</tbody></table>")

        chunks.append(
            '<p style="margin-top:1em;margin-bottom:0.4em;"><strong>Teardown</strong></p>'
        )
        chunks.append(tc["teardown_html"])
        chunks.append("<hr/>")

    out = "\n".join(chunks)
    validate_livedoc_home_html_policy(out)
    return out
