#!/usr/bin/env python3
"""Connect to Jira Cloud/Server using token-based authentication from .env."""

from __future__ import annotations

import argparse
import base64
import json
import ssl
from pathlib import Path
from typing import Any
from urllib import error, parse, request


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


def adf_to_plain_text(node: Any) -> str:
    """Convert Jira ADF (Atlassian Document Format) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(part for part in (adf_to_plain_text(item) for item in node) if part)
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type")
    if node_type == "text":
        return node.get("text", "")

    children = node.get("content") or []
    parts = [adf_to_plain_text(child) for child in children]
    joined = "\n".join(part for part in parts if part)

    if node_type in {
        "paragraph",
        "heading",
        "bulletList",
        "orderedList",
        "listItem",
        "tableRow",
        "tableCell",
        "tableHeader",
        "table",
        "blockquote",
        "codeBlock",
    }:
        return joined
    return "".join(parts)


def _ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


class JiraAdapter:
    """Adapter for Jira API with token auth from .env."""

    def __init__(self, base_url: str, token: str, email: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.email = email

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> JiraAdapter:
        path = env_file or Path(__file__).resolve().parent.parent / ".env"
        env_values = read_env_values(path)
        base_url = env_values.get("JIRA_BASE_URL")
        token = env_values.get("JIRA_TOKEN")
        email = env_values.get("JIRA_EMAIL")
        if not base_url:
            raise RuntimeError(
                f"Missing JIRA_BASE_URL in '{path}'. Copy .env.example to .env and set Jira credentials."
            )
        if not token:
            raise RuntimeError(
                f"Missing JIRA_TOKEN in '{path}'. Copy .env.example to .env and set Jira credentials."
            )
        return cls(base_url=base_url, token=token, email=email)

    def _authorization_header(self) -> str:
        if self.email:
            credentials = f"{self.email}:{self.token}".encode("utf-8")
            encoded = base64.b64encode(credentials).decode("utf-8")
            return f"Basic {encoded}"
        return f"Bearer {self.token}"

    def _request_json(self, path: str, query: dict[str, str | int] | None = None) -> dict:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"

        req = request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": self._authorization_header(),
            },
            method="GET",
        )
        context = _ssl_context()
        try:
            with request.urlopen(req, context=context) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Jira API request failed ({exc.code}) for {path}: {body}"
            ) from exc

    def get_current_user(self) -> dict:
        return self._request_json("/rest/api/3/myself")

    def list_projects(self, limit: int = 10) -> list[dict]:
        data = self._request_json("/rest/api/3/project/search", {"maxResults": limit})
        return data.get("values", [])

    def get_issue(
        self,
        issue_key: str,
        *,
        fields: str | None = None,
    ) -> dict:
        query: dict[str, str | int] = {}
        if fields:
            query["fields"] = fields
        return self._request_json(f"/rest/api/3/issue/{issue_key}", query or None)

    def get_remote_issue_links(self, issue_key: str) -> list[dict]:
        data = self._request_json(f"/rest/api/3/issue/{issue_key}/remotelink")
        return data if isinstance(data, list) else []

    def issue_summary(self, issue_key: str) -> dict[str, Any]:
        """Fetch common Epic fields and normalize description to plain text."""
        default_fields = (
            "summary,description,status,assignee,reporter,issuelinks,labels,components"
        )
        issue = self.get_issue(issue_key, fields=default_fields)
        fields = issue.get("fields") or {}
        description = fields.get("description")
        return {
            "key": issue.get("key", issue_key),
            "summary": fields.get("summary"),
            "status": (fields.get("status") or {}).get("name"),
            "assignee": (fields.get("assignee") or {}).get("displayName"),
            "reporter": (fields.get("reporter") or {}).get("displayName"),
            "labels": fields.get("labels") or [],
            "components": [
                c.get("name") for c in (fields.get("components") or []) if isinstance(c, dict)
            ],
            "description_plain": adf_to_plain_text(description),
            "description_adf": description,
            "issuelinks": fields.get("issuelinks") or [],
            "remote_links": self.get_remote_issue_links(issue_key),
        }


def main() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    env_values = read_env_values(env_file)

    parser = argparse.ArgumentParser(
        description="Validate Jira token auth, list projects, or fetch an issue."
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Jira base URL. Defaults to JIRA_BASE_URL in .env.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Jira token. Defaults to JIRA_TOKEN in .env.",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Jira email for Basic auth. Defaults to JIRA_EMAIL in .env.",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List projects after authentication check.",
    )
    parser.add_argument(
        "--issue",
        metavar="KEY",
        help="Fetch issue summary JSON (e.g. CNF-20333).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Project list limit when using --list-projects.",
    )
    args = parser.parse_args()

    base_url = args.base_url or env_values.get("JIRA_BASE_URL")
    token = args.token or env_values.get("JIRA_TOKEN")
    email = args.email or env_values.get("JIRA_EMAIL")

    if not base_url:
        raise RuntimeError(
            f"Missing Jira URL. Set JIRA_BASE_URL in '{env_file}' or pass --base-url."
        )
    if not token:
        raise RuntimeError(
            f"Missing Jira token. Set JIRA_TOKEN in '{env_file}' or pass --token."
        )

    adapter = JiraAdapter(base_url=base_url, token=token, email=email)
    me = adapter.get_current_user()
    account_id = me.get("accountId", "unknown")
    display_name = me.get("displayName", "unknown")
    print(f"Connected to Jira as '{display_name}' (accountId={account_id})")

    if args.issue:
        summary = adapter.issue_summary(args.issue.upper())
        print(json.dumps(summary, indent=2))

    if args.list_projects:
        projects = adapter.list_projects(limit=args.limit)
        print(f"Projects ({len(projects)}):")
        for project in projects:
            key = project.get("key", "?")
            name = project.get("name", "?")
            print(f"- {key}: {name}")


if __name__ == "__main__":
    main()
