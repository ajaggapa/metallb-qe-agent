"""Unit tests for Polarion LiveDoc home HTML policy (no macro footer)."""

from __future__ import annotations

import unittest

from adapters.polarion_livedoc import (
    build_livedoc_home_html,
    validate_livedoc_home_html_policy,
)


class TestValidateLivedocHomeHtmlPolicy(unittest.TestCase):
    def test_rejects_module_workitem_macro(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_livedoc_home_html_policy(
                "<p>{module-workitem:space/doc}</p>"
            )
        self.assertIn("module-workitem", str(ctx.exception).lower())

    def test_rejects_linked_section_title(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_livedoc_home_html_policy(
                "<h2>Linked Polarion test cases</h2>"
            )
        self.assertIn("linked polarion", str(ctx.exception).lower())

    def test_accepts_portal_workitem_url(self) -> None:
        # Portal links use /workitem?id= — must not false-positive on module-workitem
        validate_livedoc_home_html_policy(
            '<a href="https://example.com/polarion/redirect/project/P/workitem?id=OCP-1">OCP-1</a>'
        )


class TestBuildLivedocHomeHtml(unittest.TestCase):
    def test_minimal_build_passes_policy(self) -> None:
        html_out = build_livedoc_home_html(
            document_h1_title="Doc",
            traceability_html="<p>Trace</p>",
            tests=[
                {
                    "title": "TC-01 Example",
                    "description_html": "<p>D</p>",
                    "setup_html": "<p>S</p>",
                    "teardown_html": "<p>T</p>",
                    "steps": [("do", "see")],
                }
            ],
            project_id="OCP",
            base_url="https://example.com",
            work_item_ids=["OCP-99999"],
        )
        validate_livedoc_home_html_policy(html_out)
        self.assertIn("TC-01 Example", html_out)
        self.assertIn("workitem?id=OCP-99999", html_out)


if __name__ == "__main__":
    unittest.main()
