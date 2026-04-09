#!/usr/bin/env python3
"""Connect to Polarion using token auth from .env.

Also provides helpers to create test-case work items with Setup / Teardown / Test Steps
(two-column Polarion steps: step + expectedResult), attach them to a LiveDoc module, and
**PATCH the module home page** with readable HTML (see `polarion_livedoc.build_livedoc_home_html`
and `.cursor/rules/metallb-polarion-livedoc-workflow.mdc`).
"""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
from typing import Any, Sequence


def read_env_values(env_file: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_file.exists():
        return values

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def polarion_html_field(inner_html: str) -> dict[str, Any]:
    """Polarion rich-text field payload (HTML)."""
    return {"type": "text/html", "value": inner_html}


def html_paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def html_block(text: str) -> str:
    """
    Rich text for Polarion testcase step cells: preserve line breaks but allow word wrap
    (avoid raw <pre> without wrap — Polarion/wiki UIs often do not shrink-to-fit).
    """
    t = text.strip()
    esc = html.escape(t)
    style = (
        "white-space:pre-wrap;"
        "overflow-wrap:break-word;"
        "word-wrap:break-word;"
        "word-break:break-word;"
        "font-family:monospace,monospace;"
        "font-size:12px;"
        "line-height:1.4;"
        "margin:0;"
    )
    return f'<div style="{style}">{esc}</div>'


def build_teststeps_post_body(
    step_expected_pairs: Sequence[tuple[str, str]],
) -> Any:
    """
    Build JSON:API body for POST .../workitems/{id}/teststeps.
    Each pair is (Step column, Expected Result column), plain text; HTML is escaped.
    """
    from polarion_rest_client.openapi.models.teststeps_list_post_request import (
        TeststepsListPostRequest,
    )

    data: list[dict[str, Any]] = []
    for step_text, expected_text in step_expected_pairs:
        data.append(
            {
                "type": "teststeps",
                "attributes": {
                    "keys": ["step", "expectedResult"],
                    "values": [
                        {"type": "text/html", "value": html_block(step_text)},
                        {"type": "text/html", "value": html_block(expected_text)},
                    ],
                },
            }
        )
    return TeststepsListPostRequest.from_dict({"data": data})


class PolarionAdapter:
    """Adapter for Polarion REST API with token auth from .env."""

    def __init__(self, base_url: str, project_id: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.token = token
        self.client = self._build_client()

    def _build_client(self):
        try:
            import polarion_rest_client as prc
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency 'polarion-rest-client'. "
                "Install it with: pip install polarion-rest-client"
            ) from exc

        os.environ["POLARION_URL"] = self.base_url
        os.environ["POLARION_TOKEN"] = self.token

        return prc.PolarionClient(**prc.get_env_vars())

    def get_project(self) -> dict:
        from polarion_rest_client.project import Project

        project_api = Project(self.client)
        return project_api.get(self.project_id)

    def get_work_item(self, work_item_id: str) -> dict:
        from polarion_rest_client.workitem import WorkItem

        work_item_api = WorkItem(self.client)
        return work_item_api.get(self.project_id, work_item_id)

    def update_document_home_page(
        self,
        space_id: str,
        document_name: str,
        *,
        html_body: str,
    ) -> dict:
        """
        PATCH LiveDoc home page content (HTML shown in the wiki document body).

        If ``html_body`` was not produced by ``build_livedoc_home_html``, call
        ``polarion_livedoc.validate_livedoc_home_html_policy(html_body)`` first so the
        same no-macro-footer rules apply.
        """
        from polarion_rest_client.document import Document

        return Document(self.client).update(
            self.project_id,
            space_id,
            document_name,
            home_page_content=html_body,
            home_page_content_type="text/html",
        )

    def publish_livedoc_home_page(
        self,
        space_id: str,
        document_name: str,
        *,
        document_h1_title: str,
        traceability_html: str,
        tests: list[dict[str, Any]],
        work_item_ids: Sequence[str],
    ) -> dict:
        """
        Build standard testcase-collection HTML (via `polarion_livedoc`) and PATCH the LiveDoc home page.
        Mandatory whenever testcase work items are attached to a module — see project rules.

        The HTML builder rejects a trailing "Linked Polarion test cases" section and
        ``module-workitem`` macros (`validate_livedoc_home_html_policy`).
        """
        from .polarion_livedoc import build_livedoc_home_html

        body = build_livedoc_home_html(
            document_h1_title=document_h1_title,
            traceability_html=traceability_html,
            tests=tests,
            project_id=self.project_id,
            base_url=self.base_url,
            work_item_ids=work_item_ids,
        )
        return self.update_document_home_page(space_id, document_name, html_body=body)

    def create_module_document(
        self,
        space_id: str,
        module_name: str,
        *,
        title: str | None = None,
        doc_type: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Create a LiveDoc / module document (POST .../spaces/{space}/documents)."""
        from polarion_rest_client.document import Document

        doc_api = Document(self.client)
        return doc_api.create(
            self.project_id,
            space_id,
            module_name=module_name,
            title=title,
            doc_type=doc_type,
            status=status,
        )

    def create_testcase(
        self,
        *,
        title: str,
        description_html: str,
        setup_html: str,
        teardown_html: str,
        status: str = "draft",
    ) -> str:
        """
        Create a testcase work item and set Description, Setup, Teardown (HTML).
        Returns the short work item id (e.g. OCP-12345).
        """
        from polarion_rest_client.workitem import WorkItem

        wi = WorkItem(self.client)
        created = wi.create(
            self.project_id,
            wi_type="testcase",
            title=title,
            attributes={"status": status},
        )
        wid = str(created.get("id", "")).split("/")[-1]
        if not wid:
            raise RuntimeError(f"Unexpected create response: {created!r}")

        wi.update(
            self.project_id,
            wid,
            description=description_html,
            description_type="text/html",
            attributes={
                "setup": polarion_html_field(setup_html),
                "teardown": polarion_html_field(teardown_html),
            },
        )
        return wid

    def add_test_steps(
        self,
        work_item_id: str,
        step_expected_pairs: Sequence[tuple[str, str]],
    ) -> None:
        """Append test steps (Step | Expected Result) to an existing testcase."""
        from polarion_rest_client.error import raise_from_response
        from polarion_rest_client.openapi.api.test_steps.post_test_steps import (
            sync_detailed as post_test_steps,
        )

        body = build_teststeps_post_body(step_expected_pairs)
        resp = post_test_steps(
            client=self.client.gen,
            project_id=self.project_id,
            work_item_id=work_item_id,
            body=body,
        )
        if resp.status_code != 201:
            raise_from_response(resp)

    def delete_all_test_steps(self, work_item_id: str) -> None:
        """Remove every test step from a testcase (GET include=testSteps, then batch DELETE)."""
        from polarion_rest_client.error import raise_from_response
        from polarion_rest_client.openapi.api.test_steps.delete_test_steps import (
            sync_detailed as delete_test_steps,
        )
        from polarion_rest_client.openapi.models.teststeps_list_delete_request import (
            TeststepsListDeleteRequest,
        )
        from polarion_rest_client.workitem import WorkItem

        raw = WorkItem(self.client).get(
            self.project_id, work_item_id, include="testSteps"
        )
        included = raw.get("included") or []
        to_delete = [
            {"type": "teststeps", "id": item["id"]}
            for item in included
            if item.get("type") == "teststeps" and item.get("id")
        ]
        if not to_delete:
            return
        body = TeststepsListDeleteRequest.from_dict({"data": to_delete})
        resp = delete_test_steps(
            client=self.client.gen,
            project_id=self.project_id,
            work_item_id=work_item_id,
            body=body,
        )
        if resp.status_code not in (200, 204):
            raise_from_response(resp)

    def replace_test_steps(
        self,
        work_item_id: str,
        step_expected_pairs: Sequence[tuple[str, str]],
    ) -> None:
        """Replace testcase steps: delete existing rows, then POST new Step | Expected Result pairs."""
        self.delete_all_test_steps(work_item_id)
        self.add_test_steps(work_item_id, step_expected_pairs)

    def delete_work_items(self, work_item_ids: Sequence[str]) -> None:
        """Delete work items by short id (e.g. OCP-12345)."""
        from polarion_rest_client.workitem import WorkItem

        if not work_item_ids:
            return
        WorkItem(self.client).delete(self.project_id, list(work_item_ids))

    def move_workitem_to_document(
        self,
        work_item_id: str,
        target_document: str,
    ) -> None:
        """
        Move a work item into a LiveDoc module.
        target_document format: {projectId}/{spaceId}/{moduleName}
        Example: OSE/OpenShift/CNF_20333_MetalLB_Tests
        """
        from polarion_rest_client.workitem import WorkItem

        WorkItem(self.client).move_to_document(
            self.project_id,
            work_item_id,
            target_document=target_document,
        )


def main() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    env_values = read_env_values(env_file)

    parser = argparse.ArgumentParser(
        description="Validate Polarion token auth and optionally fetch a work item."
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Polarion base URL. Defaults to POLARION_BASE_URL in .env.",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="Polarion project ID. Defaults to POLARION_PROJECT_ID in .env.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Polarion token. Defaults to POLARION_TOKEN in .env.",
    )
    parser.add_argument(
        "--work-item",
        default=None,
        help="Optional work item id to fetch (e.g. OSE-12345).",
    )
    args = parser.parse_args()

    base_url = args.base_url or env_values.get("POLARION_BASE_URL")
    project_id = args.project_id or env_values.get("POLARION_PROJECT_ID")
    token = args.token or env_values.get("POLARION_TOKEN")

    if not base_url:
        raise RuntimeError(
            f"Missing Polarion URL. Set POLARION_BASE_URL in '{env_file}' or pass --base-url."
        )
    if not project_id:
        raise RuntimeError(
            f"Missing Polarion project id. Set POLARION_PROJECT_ID in '{env_file}' or pass --project-id."
        )
    if not token:
        raise RuntimeError(
            f"Missing Polarion token. Set POLARION_TOKEN in '{env_file}' or pass --token."
        )

    adapter = PolarionAdapter(base_url=base_url, project_id=project_id, token=token)
    project = adapter.get_project()
    print(f"Connected to Polarion project '{project_id}'")
    print(project)

    if args.work_item:
        work_item = adapter.get_work_item(args.work_item)
        print(f"Work item '{args.work_item}':")
        print(work_item)


if __name__ == "__main__":
    main()
