#!/usr/bin/env python3
"""Connect to Polarion using token auth from .env.

Also provides helpers to create test-case work items with Setup / Teardown / Test Steps
(two-column Polarion steps: step + expectedResult), attach them to a LiveDoc module, and
**PATCH the module home page** with readable HTML (see `polarion_livedoc.build_livedoc_home_html`
and `.cursor/skills/metallb-polarion-test-publish/references/metallb-polarion-livedoc-workflow.mdc`).
"""

from __future__ import annotations

import argparse
import html
import os
import re
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


# Process environment overrides for one-off runs (export VAR=... wins over .env for these keys).
_QE_SHELL_OVERRIDE_PREFIXES = ("POLARION_", "METALLB_", "JIRA_")
_QE_SHELL_OVERRIDE_EXACT: frozenset[str] = frozenset({"KUBECONFIG"})


def read_qe_env(env_file: Path) -> dict[str, str]:
    """
    Load ``.env`` then overlay matching variables from ``os.environ``.

    Use this for publish scripts so operators can pass ``METALLB_JIRA_EPIC_KEY``,
    ``POLARION_TRACE_*``, or ``KUBECONFIG`` from the shell without editing ``.env``.
    """
    values = read_env_values(env_file)
    for key, raw in os.environ.items():
        v = raw.strip() if isinstance(raw, str) else ""
        if not v:
            continue
        if key in _QE_SHELL_OVERRIDE_EXACT or key.startswith(_QE_SHELL_OVERRIDE_PREFIXES):
            values[key] = v
    return values


def build_livedoc_portal_url(
    base_url: str,
    project_id: str,
    space_id: str,
    module_name: str,
) -> str:
    """
    Browser URL for a Polarion LiveDoc module home page.

    Red Hat Polarion SPA routing uses ``#/project/{projectId}/wiki/{spaceId}/{moduleName}``.
    Do **not** use ``#/project/.../space/.../module/...`` — that path redirects to the portal home.
    """
    base = base_url.rstrip("/")
    return f"{base}/polarion/#/project/{project_id}/wiki/{space_id}/{module_name}"


def livedoc_module_location(space_id: str, module_name: str) -> str:
    """Polarion module location for SOAP ``getModuleByLocation`` (``{space}/{moduleName}``)."""
    return f"{space_id}/{module_name}"


def _soap_login_session_id(*, base_url: str, token: str, http_client: Any) -> str:
    session_url = f"{base_url.rstrip('/')}/polarion/ws/services/SessionWebService"
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ses="http://ws.polarion.com/SessionWebService">
  <soapenv:Body><ses:logInWithToken><ses:mechanism>AccessToken</ses:mechanism><ses:username></ses:username><ses:token>{html.escape(token)}</ses:token></ses:logInWithToken></soapenv:Body>
</soapenv:Envelope>"""
    resp = http_client.post(
        session_url,
        content=body.encode(),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "logInWithToken"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Polarion SOAP login failed (HTTP {resp.status_code})")
    match = re.search(r"<ns1:sessionID[^>]*>([^<]+)</ns1:sessionID>", resp.text)
    if not match:
        raise RuntimeError("Polarion SOAP login response missing sessionID")
    return match.group(1)


def _soap_tracker_call(*, base_url: str, session_id: str, body: str, action: str, http_client: Any) -> str:
    tracker_url = f"{base_url.rstrip('/')}/polarion/ws/services/TrackerWebService"
    resp = http_client.post(
        tracker_url,
        content=body.encode(),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": action},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Polarion SOAP {action} failed (HTTP {resp.status_code})")
    return resp.text


def build_livedoc_portal_url_from_target(
    base_url: str,
    target_document: str,
) -> str:
    """
    Build a LiveDoc portal URL from REST ``target_document`` ``{projectId}/{spaceId}/{moduleName}``.
    """
    parts = target_document.split("/", 2)
    if len(parts) != 3:
        raise ValueError(
            f"target_document must be project/space/module, got {target_document!r}"
        )
    project_id, space_id, module_name = parts
    return build_livedoc_portal_url(base_url, project_id, space_id, module_name)


def polarion_html_field(inner_html: str) -> dict[str, Any]:
    """Polarion rich-text field payload (HTML)."""
    return {"type": "text/html", "value": inner_html}


def html_paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def module_workitem_macro_div(work_item_id: str) -> str:
    """
    Polarion LiveDoc wiki macro that **marks** a testcase work item in the document.

    Without one macro per testcase, PATCHing custom home-page HTML can leave work items
    "unmarked" (portal links alone are not enough). Use exactly one per test — no headings.
    """
    wid = html.escape(work_item_id, quote=True)
    return (
        f'<div id="polarion_wiki macro name=module-workitem;params=id={wid}"></div>'
    )


def html_section_label(
    text: str,
    *,
    margin_top: str = "1em",
    margin_bottom: str = "0.4em",
    font_size: str | None = None,
    text_decoration: str | None = None,
    bold: bool = True,
) -> str:
    """
    Bold section label as a ``<p>`` — not ``<h1>``–``<h6>``.

    Polarion turns HTML headings into LiveDoc outline Heading parts (extra IDs/nodes).
    Use this for document titles, testcase titles, and subsections on the home page and
    in testcase Description fields.

    Typography (``font-size``, underline) must live on an inner ``<span>`` — Polarion's
    wiki renderer ignores ``font-size`` on ``<p>`` (see CNF MetalLB reference LiveDocs).
    """
    p_style = f"margin-top:{margin_top};margin-bottom:{margin_bottom};"
    span_parts = ["line-height:1.5"]
    if bold:
        span_parts.append("font-weight:bold")
    if font_size:
        span_parts.append(f"font-size:{font_size}")
    if text_decoration:
        span_parts.append(f"text-decoration:{text_decoration}")
    span_style = ";".join(span_parts) + ";"
    return (
        f'<p style="{p_style}">'
        f'<span style="{span_style}">{html.escape(text)}</span></p>'
    )


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

    def update_testcase_description(
        self,
        work_item_id: str,
        description_html: str,
    ) -> None:
        """PATCH testcase Description (HTML)."""
        from polarion_rest_client.workitem import WorkItem

        WorkItem(self.client).update(
            self.project_id,
            work_item_id,
            description=description_html,
            description_type="text/html",
        )

    def publish_livedoc_home_page(
        self,
        space_id: str,
        document_name: str,
        *,
        document_h1_title: str,
        trace: dict[str, str],
        tests: list[dict[str, Any]],
        work_item_ids: Sequence[str],
    ) -> dict:
        """
        Build standard testcase-collection HTML (via `polarion_livedoc`) and PATCH the LiveDoc home page.
        Mandatory whenever testcase work items are attached to a module — see project rules.

        The HTML builder requires one ``module-workitem`` macro per testcase (marks WIs in
        the document) and rejects heading tags / a "Linked Polarion test cases" footer.
        """
        from .polarion_livedoc import build_livedoc_home_html

        body = build_livedoc_home_html(
            document_h1_title=document_h1_title,
            trace=trace,
            tests=tests,
            project_id=self.project_id,
            base_url=self.base_url,
            work_item_ids=work_item_ids,
        )
        return self.update_document_home_page(space_id, document_name, html_body=body)

    def livedoc_portal_url(self, space_id: str, module_name: str) -> str:
        """Browser URL for this project's LiveDoc module (wiki home page)."""
        return build_livedoc_portal_url(
            self.base_url, self.project_id, space_id, module_name
        )

    def delete_livedoc_module(
        self,
        space_id: str,
        module_name: str,
        *,
        project_id: str | None = None,
        confirmed: bool = False,
    ) -> None:
        """
        Delete a LiveDoc module (document).

        Polarion REST returns HTTP 405 for document DELETE. Deletion uses SOAP
        ``TrackerWebService.getModuleByLocation`` + ``deleteModule`` with the same
        ``POLARION_TOKEN`` as REST (``SessionWebService.logInWithToken``).

        Pass ``confirmed=True`` only after the user has approved deletion **twice** in chat
        (see ``adapters.polarion_deletion`` and ``metallb-polarion-deletion-guardrails``).
        """
        if not confirmed:
            raise ValueError(
                "Refusing to delete LiveDoc without confirmed=True. Build a deletion plan "
                "(build_livedoc_deletion_plan), show invalid links to the user, obtain double "
                "explicit confirmation in chat, then call delete scripts with matching "
                "--confirm-token and --confirm-final."
            )
        proj = project_id or self.project_id
        http_client = self.client.gen.get_httpx_client()
        session_id = _soap_login_session_id(
            base_url=self.base_url, token=self.token, http_client=http_client
        )
        location = livedoc_module_location(space_id, module_name)
        get_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tra="http://ws.polarion.com/TrackerWebService">
  <soapenv:Header><ns1:sessionID xmlns:ns1="http://ws.polarion.com/session">{session_id}</ns1:sessionID></soapenv:Header>
  <soapenv:Body><tra:getModuleByLocation><tra:projectId>{html.escape(proj)}</tra:projectId><tra:location>{html.escape(location)}</tra:location></tra:getModuleByLocation></soapenv:Body>
</soapenv:Envelope>"""
        get_xml = _soap_tracker_call(
            base_url=self.base_url,
            session_id=session_id,
            body=get_body,
            action="getModuleByLocation",
            http_client=http_client,
        )
        if "Fault" in get_xml:
            fault = re.search(r"<faultstring>([^<]+)</faultstring>", get_xml)
            raise RuntimeError(
                f"Polarion getModuleByLocation failed for {proj}/{location}: "
                f"{fault.group(1) if fault else get_xml[:300]}"
            )
        uri_match = re.search(r'uri="([^"]+)"', get_xml)
        if not uri_match:
            raise RuntimeError(
                f"Polarion getModuleByLocation returned no module URI for {proj}/{location}"
            )
        module_uri = uri_match.group(1)
        delete_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tra="http://ws.polarion.com/TrackerWebService">
  <soapenv:Header><ns1:sessionID xmlns:ns1="http://ws.polarion.com/session">{session_id}</ns1:sessionID></soapenv:Header>
  <soapenv:Body><tra:deleteModule><tra:moduleURI>{html.escape(module_uri)}</tra:moduleURI></tra:deleteModule></soapenv:Body>
</soapenv:Envelope>"""
        delete_xml = _soap_tracker_call(
            base_url=self.base_url,
            session_id=session_id,
            body=delete_body,
            action="deleteModule",
            http_client=http_client,
        )
        if "deleteModuleResponse" not in delete_xml:
            fault = re.search(r"<faultstring>([^<]+)</faultstring>", delete_xml)
            raise RuntimeError(
                f"Polarion deleteModule failed for {module_uri}: "
                f"{fault.group(1) if fault else delete_xml[:300]}"
            )

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
        metadata: dict[str, Any] | None = None,
        status: str = "draft",
    ) -> str:
        """
        Create a testcase work item and set Description, Setup, Teardown (HTML),
        and Polarion classification metadata.

        ``metadata`` must use Polarion REST attribute ids (see
        ``polarion_test_publish.build_testcase_metadata``): UI fields Level,
        Component, Importance, Pos/Neg, and Automation map to ``caselevel``,
        ``casecomponent``, ``caseimportance``, ``caseposneg``, and
        ``caseautomation`` — not ``level`` / ``component`` / ``importance``.
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

        attrs: dict[str, Any] = {
            "setup": polarion_html_field(setup_html),
            "teardown": polarion_html_field(teardown_html),
        }
        if metadata:
            attrs.update(metadata)

        wi.update(
            self.project_id,
            wid,
            description=description_html,
            description_type="text/html",
            attributes=attrs,
        )
        return wid

    def update_testcase_metadata(
        self,
        work_item_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """PATCH testcase classification fields (``caselevel``, ``casecomponent``, etc.)."""
        from polarion_rest_client.workitem import WorkItem

        WorkItem(self.client).update(
            self.project_id,
            work_item_id,
            attributes=metadata,
        )

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
    env_values = read_qe_env(env_file)

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
