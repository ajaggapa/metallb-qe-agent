#!/usr/bin/env python3
"""Create Google Docs test documents using OAuth credentials."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents"]


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


class GoogleDocsAdapter:
    """Adapter for Google Docs API using OAuth user credentials."""

    def __init__(self, auth_path: Path, token_path: Path):
        self.auth_path = auth_path
        self.token_path = token_path
        self.credentials = self._load_credentials()
        self.docs_service = build("docs", "v1", credentials=self.credentials)

    def _load_credentials(self):
        data = json.loads(self.auth_path.read_text(encoding="utf-8"))
        if data.get("type") == "service_account":
            raise RuntimeError(
                f"Service account auth is disabled for '{self.auth_path.name}'. "
                "Use an OAuth client auth file."
            )

        creds = None
        if self.token_path.exists():
            creds = UserCredentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.auth_path), SCOPES)
                redirect_port = int(os.getenv("OAUTH_REDIRECT_PORT", "8080"))
                creds = flow.run_local_server(port=redirect_port)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")

        return creds

    def create_document(self, title: str, content: str) -> str:
        doc = self.docs_service.documents().create(body={"title": title}).execute()
        document_id = doc["documentId"]
        self.docs_service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        ).execute()
        return document_id


def main() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    env_values = read_env_values(env_file)

    parser = argparse.ArgumentParser(
        description="Create a test Google Doc using OAuth configuration."
    )
    parser.add_argument(
        "--auth-file",
        default=None,
        help="Optional OAuth client JSON path. Defaults to OAUTH_FILE_PATH in .env.",
    )
    parser.add_argument(
        "--token-file",
        default=None,
        help="Optional token JSON path. Defaults to <auth-file>.token.json.",
    )
    parser.add_argument(
        "--content",
        default=None,
        help="Optional document content. Defaults to auth filename.",
    )
    args = parser.parse_args()

    oauth_path = args.auth_file or env_values.get("OAUTH_FILE_PATH")
    if not oauth_path:
        raise RuntimeError(
            f"Missing OAuth path. Set OAUTH_FILE_PATH in '{env_file}' or pass --auth-file."
        )

    auth_file = Path(oauth_path).expanduser().resolve()
    if not auth_file.exists():
        raise FileNotFoundError(f"Missing auth file: {auth_file}")
    token_file = (
        Path(args.token_file).expanduser().resolve()
        if args.token_file
        else auth_file.with_suffix(".token.json")
    )

    adapter = GoogleDocsAdapter(auth_file, token_file)
    content = args.content or auth_file.name
    title = f"test-doc-{auth_file.stem}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    document_id = adapter.create_document(title=title, content=content)
    print(
        f"Created Google Doc: title='{title}', id={document_id}, "
        f"url=https://docs.google.com/document/d/{document_id}/edit"
    )


if __name__ == "__main__":
    main()
