"""Unit tests for Polarion LiveDoc home HTML policy."""

from __future__ import annotations

import re
import unittest

from adapters.polarion_livedoc import (
    build_livedoc_home_html,
    validate_livedoc_home_html_policy,
)

_HEADING_RE = re.compile(r"<h[1-6][\s>]", re.IGNORECASE)
_MACRO = "module-workitem;params=id=OCP-99999"
_TRACE = {
    "epic_url": "https://example.com/epic",
    "epic_label": "EPIC-1",
    "high_level_plan_url": "https://example.com/hl",
    "detailed_plan_url": "https://example.com/dl",
}


class TestValidateLivedocHomeHtmlPolicy(unittest.TestCase):
    def test_rejects_linked_section_title(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_livedoc_home_html_policy(
                "<p><strong>Linked Polarion test cases</strong></p>"
            )
        self.assertIn("linked polarion", str(ctx.exception).lower())

    def test_rejects_heading_tags(self) -> None:
        for tag in ("h1", "h2", "h3", "h4"):
            with self.subTest(tag=tag):
                with self.assertRaises(ValueError) as ctx:
                    validate_livedoc_home_html_policy(f"<{tag}>Title</{tag}>")
                self.assertIn("heading", str(ctx.exception).lower())

    def test_requires_one_macro_per_work_item(self) -> None:
        with self.assertRaises(ValueError):
            validate_livedoc_home_html_policy(
                "<p>no macros</p>", work_item_ids=["OCP-1"]
            )
        validate_livedoc_home_html_policy(
            f'<div id="polarion_wiki macro name={_MACRO}"></div>',
            work_item_ids=["OCP-99999"],
        )


class TestBuildLivedocHomeHtml(unittest.TestCase):
    def test_prose_sections_once_per_test(self) -> None:
        html_out = build_livedoc_home_html(
            document_h1_title="Doc",
            trace=_TRACE,
            tests=[
                {
                    "title": "TC-01 Example",
                    "purpose": "purpose one",
                    "pass_fail": "pass one",
                    "setup_html": "<p>S</p>",
                    "teardown_html": "<p>T</p>",
                    "steps": [("do", "see")],
                },
                {
                    "title": "TC-02 Other",
                    "purpose": "purpose two",
                    "pass_fail": "pass two",
                    "setup_html": "<p>S2</p>",
                    "teardown_html": "<p>T2</p>",
                    "steps": [("x", "y")],
                },
            ],
            project_id="OCP",
            base_url="https://example.com",
            work_item_ids=["OCP-99999", "OCP-88888"],
        )
        validate_livedoc_home_html_policy(
            html_out, work_item_ids=["OCP-99999", "OCP-88888"]
        )
        self.assertEqual(html_out.count(">Traceability</span>"), 2)
        self.assertEqual(html_out.count(">Purpose</span>"), 2)
        self.assertEqual(html_out.count(">Pass / fail (summary)</span>"), 2)
        self.assertNotIn(">Description</span>", html_out)
        intro_end = html_out.find("module-workitem")
        self.assertNotIn(">Traceability</span>", html_out[:intro_end])
        self.assertIsNone(_HEADING_RE.search(html_out))

    def test_heading_font_sizes_and_testcase_underline(self) -> None:
        html_out = build_livedoc_home_html(
            document_h1_title="Main Doc Title",
            trace=_TRACE,
            tests=[
                {
                    "title": "TC-01 Example",
                    "purpose": "p",
                    "pass_fail": "pf",
                    "setup_html": "<p>S</p>",
                    "teardown_html": "<p>T</p>",
                    "steps": [("do", "see")],
                },
            ],
            project_id="OCP",
            base_url="https://example.com",
            work_item_ids=["OCP-99999"],
        )
        self.assertIn("font-size:16pt", html_out)
        self.assertNotRegex(html_out, r'<p style="[^"]*font-size:16pt')
        tc_title = html_out.split("module-workitem", 1)[1]
        self.assertIn("font-size:12pt", tc_title)
        self.assertIn("text-decoration:underline", tc_title)
        self.assertIn(">TC-01 Example</span>", tc_title)
        self.assertNotRegex(tc_title, r'<p style="[^"]*font-size:12pt')


if __name__ == "__main__":
    unittest.main()
