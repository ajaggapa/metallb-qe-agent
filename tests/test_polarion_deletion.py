"""Unit tests for Polarion deletion guardrails."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from adapters.polarion_deletion import (
    LivedocDeletionPlan,
    WorkItemDeletionEntry,
    WorkItemsDeletionPlan,
    build_livedoc_deletion_plan,
    format_livedoc_deletion_plan_markdown,
    require_dual_confirmation,
)


class TestDeletionConfirmTokens(unittest.TestCase):
    def test_livedoc_confirm_token(self) -> None:
        plan = LivedocDeletionPlan(
            project_id="OSE",
            space_id="CNF",
            module_name="CNF_20333_MetalLB_ConfigurationState",
            target_document="OSE/CNF/CNF_20333_MetalLB_ConfigurationState",
            livedoc_url="https://example.com/polarion/#/project/OSE/wiki/CNF/CNF_20333_MetalLB_ConfigurationState",
            module_title="Test",
        )
        self.assertEqual(
            plan.confirm_token,
            "DELETE-LIVEDOC:OSE/CNF/CNF_20333_MetalLB_ConfigurationState",
        )

    def test_work_items_confirm_token_sorted(self) -> None:
        plan = WorkItemsDeletionPlan(
            project_id="OSE",
            work_items=(
                WorkItemDeletionEntry("OCP-89306", "B", "https://example.com/2"),
                WorkItemDeletionEntry("OCP-89305", "A", "https://example.com/1"),
            ),
        )
        self.assertEqual(plan.confirm_token, "DELETE-WORK-ITEMS:OCP-89305,OCP-89306")


class TestRequireDualConfirmation(unittest.TestCase):
    def test_refuses_without_flags(self) -> None:
        with self.assertRaises(SystemExit):
            require_dual_confirmation(None, None, "DELETE-LIVEDOC:OSE/CNF/x")

    def test_refuses_mismatched_tokens(self) -> None:
        with self.assertRaises(SystemExit):
            require_dual_confirmation("wrong", "wrong", "DELETE-LIVEDOC:OSE/CNF/x")

    def test_accepts_matching_pair(self) -> None:
        token = "DELETE-LIVEDOC:OSE/CNF/x"
        require_dual_confirmation(token, token, token)


class TestFormatDeletionPlan(unittest.TestCase):
    def test_markdown_lists_invalid_livedoc_url(self) -> None:
        plan = LivedocDeletionPlan(
            project_id="OSE",
            space_id="CNF",
            module_name="Mod",
            target_document="OSE/CNF/Mod",
            livedoc_url="https://example.com/wiki",
            module_title="Title",
            work_items=(
                WorkItemDeletionEntry(
                    "OCP-1",
                    "TC-01",
                    "https://example.com/wi/OCP-1",
                ),
            ),
        )
        md = format_livedoc_deletion_plan_markdown(plan)
        self.assertIn("https://example.com/wiki", md)
        self.assertIn("OCP-1", md)
        self.assertIn(plan.confirm_token, md)
        self.assertIn("two separate chat turns", md)


class TestBuildLivedocDeletionPlan(unittest.TestCase):
    def test_extracts_work_items_from_home_page_macros(self) -> None:
        adapter = MagicMock()
        adapter.base_url = "https://polarion.example.com"
        adapter.project_id = "OSE"
        adapter.client = MagicMock()
        adapter.get_work_item.return_value = {
            "data": {"attributes": {"title": "CNF-20333 TC-01"}}
        }

        doc_api = MagicMock()
        doc_api.get.return_value = {
            "data": {
                "attributes": {
                    "title": "Test module",
                    "homePageContent": {
                        "type": "text/html",
                        "value": (
                            '<div id="polarion_wiki macro name=module-workitem;params=id=OCP-89305"></div>'
                            '<div id="polarion_wiki macro name=module-workitem;params=id=OCP-89306"></div>'
                        ),
                    },
                }
            }
        }

        import adapters.polarion_deletion as pd

        original = __import__("polarion_rest_client.document", fromlist=["Document"]).Document
        try:
            import polarion_rest_client.document as doc_mod

            doc_mod.Document = MagicMock(return_value=doc_api)
            plan = build_livedoc_deletion_plan(adapter, "CNF", "Mod", project_id="OSE")
        finally:
            doc_mod.Document = original

        self.assertEqual(len(plan.work_items), 2)
        self.assertEqual(plan.work_items[0].work_item_id, "OCP-89305")


if __name__ == "__main__":
    unittest.main()
