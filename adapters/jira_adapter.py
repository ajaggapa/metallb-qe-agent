#!/usr/bin/env python3
"""Connect to Jira Cloud/Server using token-based authentication."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
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


class JiraAdapter:
    """Adapter for Jira API with token auth from .env."""

    def __init__(self, base_url: str, token: str, email: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.email = email

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
        try:
            with request.urlopen(req) as resp:
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


def main() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    env_values = read_env_values(env_file)

    parser = argparse.ArgumentParser(
        description="Validate Jira token auth and optionally list projects."
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

    if args.list_projects:
        projects = adapter.list_projects(limit=args.limit)
        print(f"Projects ({len(projects)}):")
        for project in projects:
            key = project.get("key", "?")
            name = project.get("name", "?")
            print(f"- {key}: {name}")


if __name__ == "__main__":
    main()
