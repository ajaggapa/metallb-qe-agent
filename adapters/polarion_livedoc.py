"""
Reusable Polarion LiveDoc home-page HTML for testcase collections.

Embeds full readable testcase content on the home page plus one ``module-workitem`` macro
per testcase so Polarion keeps each work item **marked** in the document (portal links alone
cause "unmarked in the Document" warnings). Use bold ``<p>`` labels only — never ``<h1>``–``<h6>``.
"""

from __future__ import annotations

import html
import re
from typing import Any, Sequence

from .polarion_adapter import html_section_label, module_workitem_macro_div
from .polarion_test_publish import livedoc_purpose_pass_fail_html, traceability_ul

_FORBIDDEN_SECTION_TITLE = "linked polarion test cases"
_HEADING_TAG_RE = re.compile(r"<h[1-6][\s>]", re.IGNORECASE)
_MACRO_ID_RE = re.compile(
    r"module-workitem;params=id=([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)


def validate_livedoc_home_html_policy(
    html_body: str,
    *,
    work_item_ids: Sequence[str] | None = None,
) -> None:
    """
    Ensure home-page HTML matches project policy.

    When ``work_item_ids`` is provided, requires exactly one ``module-workitem`` macro per id.
    """
    lower = html_body.casefold()
    if _FORBIDDEN_SECTION_TITLE in lower:
        raise ValueError(
            'LiveDoc home HTML must not contain a "Linked Polarion test cases" section.'
        )
    if _HEADING_TAG_RE.search(html_body):
        raise ValueError(
            "LiveDoc home HTML must not contain <h1>–<h6> heading tags; Polarion creates "
            "extra outline Heading nodes from them. Use html_section_label() / bold <p> instead."
        )
    if work_item_ids is not None:
        expected = list(work_item_ids)
        found = _MACRO_ID_RE.findall(html_body)
        if len(found) != len(expected):
            raise ValueError(
                f"LiveDoc home HTML must contain exactly one module-workitem macro per "
                f"testcase ({len(expected)} expected, {len(found)} found)."
            )
        if found != expected:
            raise ValueError(
                "module-workitem macro ids must match work_item_ids in the same testcase order."
            )


def build_livedoc_home_html(
    *,
    document_h1_title: str,
    trace: dict[str, str],
    tests: list[dict[str, Any]],
    project_id: str,
    base_url: str,
    work_item_ids: Sequence[str],
) -> str:
    """
    Build full HTML for a LiveDoc module home page.

    Each testcase block includes:
      - one ``module-workitem`` macro (marks the WI in the document outline)
      - **Traceability**, **Purpose**, **Pass/fail** once under the test (not on WI Description)
      - Setup, step table, Teardown (WI Description left empty to avoid macro duplication)
    """
    base = base_url.rstrip("/")
    ids = list(work_item_ids)
    if len(ids) != len(tests):
        raise ValueError(
            f"work_item_ids length ({len(ids)}) must match tests length ({len(tests)})"
        )

    chunks: list[str] = []

    chunks.append('<p id="polarion_1"></p>')
    chunks.append(
        html_section_label(
            document_h1_title,
            margin_top="0",
            margin_bottom="0.6em",
            font_size="16pt",
        )
    )
    chunks.append(html_section_label("Contents", margin_top="1em"))
    chunks.append("<ul>")
    for tc in tests:
        chunks.append(f"<li>{html.escape(tc['title'])}</li>")
    chunks.append("</ul>")

    for tc, wid in zip(tests, ids, strict=True):
        portal = f"{base}/polarion/redirect/project/{project_id}/workitem?id={wid}"
        chunks.append(module_workitem_macro_div(wid))
        chunks.append(
            html_section_label(
                tc["title"],
                margin_top="1.5em",
                font_size="12pt",
                text_decoration="underline",
            )
        )
        chunks.append(
            "<p><strong>Polarion test case:</strong> "
            f'<a href="{html.escape(portal, quote=True)}">{html.escape(wid)}</a></p>'
        )

        chunks.append(
            html_section_label("Traceability", margin_top="1em", margin_bottom="0.4em")
            + traceability_ul(trace)
        )
        purpose = str(tc["purpose"]).strip()
        pass_fail = str(tc["pass_fail"]).strip()
        chunks.append(livedoc_purpose_pass_fail_html(purpose, pass_fail))

        chunks.append(html_section_label("Setup", margin_top="1em", margin_bottom="0.4em"))
        chunks.append(tc["setup_html"])

        chunks.append(
            html_section_label("Test steps", margin_top="1em", margin_bottom="0.4em")
        )
        chunks.append(
            '<table border="1" cellpadding="6" cellspacing="0" '
            'style="border-collapse:collapse;width:100%;table-layout:fixed;">'
        )
        chunks.append(
            "<thead><tr>"
            '<th scope="col" style="text-align:left;width:50%;">Step</th>'
            '<th scope="col" style="text-align:left;width:50%;">Expected Result</th>'
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
            html_section_label("Teardown", margin_top="1em", margin_bottom="0.4em")
        )
        chunks.append(tc["teardown_html"])
        chunks.append("<hr/>")

    out = "\n".join(chunks)
    validate_livedoc_home_html_policy(out, work_item_ids=ids)
    return out
