"""Unit tests for Polarion portal URL builders."""

from __future__ import annotations

import unittest

from adapters.polarion_adapter import (
    build_livedoc_portal_url,
    build_livedoc_portal_url_from_target,
    livedoc_module_location,
)


class TestPolarionPortalUrls(unittest.TestCase):
    def test_livedoc_wiki_route(self) -> None:
        url = build_livedoc_portal_url(
            "https://polarion.engineering.redhat.com",
            "OSE",
            "CNF",
            "CNF_20333_MetalLB_ConfigurationState",
        )
        self.assertEqual(
            url,
            "https://polarion.engineering.redhat.com/polarion/#/project/OSE/wiki/CNF/CNF_20333_MetalLB_ConfigurationState",
        )
        self.assertNotIn("/space/", url)
        self.assertNotIn("/module/", url)

    def test_from_target_document(self) -> None:
        url = build_livedoc_portal_url_from_target(
            "https://example.com/",
            "OSE/CNF/CNF_20333_MetalLB_ConfigurationState",
        )
        self.assertEqual(
            url,
            "https://example.com/polarion/#/project/OSE/wiki/CNF/CNF_20333_MetalLB_ConfigurationState",
        )


    def test_module_location(self) -> None:
        self.assertEqual(
            livedoc_module_location("CNF", "CNF_20333_MetalLB_ConfigurationState"),
            "CNF/CNF_20333_MetalLB_ConfigurationState",
        )


if __name__ == "__main__":
    unittest.main()
