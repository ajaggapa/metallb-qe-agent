#!/usr/bin/env python3
"""Publish a markdown test plan to Google Docs with rich formatting."""

from __future__ import annotations

import argparse
import errno
import json
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


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


def load_credentials(auth_file: Path, token_file: Path, redirect_port: int) -> UserCredentials:
    creds: UserCredentials | None = None
    if token_file.exists():
        try:
            creds = UserCredentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception:
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(str(auth_file), SCOPES)
    # open_browser=False keeps behavior stable in agent sessions.
    try:
        creds = flow.run_local_server(
            port=redirect_port,
            open_browser=False,
            prompt="consent",
            access_type="offline",
        )
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise RuntimeError(
                f"OAuth callback port {redirect_port} is already in use. "
                "Close the other running OAuth flow/agent and retry."
            ) from exc
        raise
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_doc_requests(markdown_lines: list[str]) -> tuple[str, list[dict]]:
    text = ""
    paragraph_styles: list[tuple[int, int, str]] = []
    bullet_lines: list[tuple[int, int, bool]] = []
    bold_ranges: list[tuple[int, int]] = []
    link_ranges: list[tuple[int, int, str]] = []

    idx = 1
    url_rx = re.compile(r"https?://[^\s)]+")

    for raw_line in markdown_lines:
        line = raw_line.rstrip("\n")
        named_style = None
        ordered = None

        if line.startswith("# "):
            named_style = "TITLE"
            content = line[2:].strip()
        elif line.startswith("## "):
            named_style = "HEADING_2"
            content = line[3:].strip()
        elif line.startswith("### "):
            named_style = "HEADING_3"
            content = line[4:].strip()
        elif re.match(r"^\s*\d+\.\s+", line):
            ordered = True
            content = re.sub(r"^\s*\d+\.\s+", "", line)
        elif re.match(r"^\s*-\s+", line):
            ordered = False
            content = re.sub(r"^\s*-\s+", "", line)
        else:
            content = line

        out = ""
        i = 0
        local_bold: list[tuple[int, int]] = []
        while i < len(content):
            if content.startswith("**", i):
                j = content.find("**", i + 2)
                if j != -1:
                    segment = content[i + 2 : j]
                    seg_start = len(out)
                    out += segment
                    seg_end = len(out)
                    local_bold.append((seg_start, seg_end))
                    i = j + 2
                    continue
            out += content[i]
            i += 1

        start = idx
        text += out + "\n"
        end = idx + len(out)

        if named_style and out:
            paragraph_styles.append((start, end, named_style))
        if ordered is not None and out:
            bullet_lines.append((start, end, ordered))
        for s, e in local_bold:
            if s != e:
                bold_ranges.append((start + s, start + e))
        for m in url_rx.finditer(out):
            link_ranges.append((start + m.start(), start + m.end(), m.group(0)))

        idx += len(out) + 1

    requests: list[dict] = [{"insertText": {"location": {"index": 1}, "text": text}}]
    for s, e, style in paragraph_styles:
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": s, "endIndex": e + 1},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType",
                }
            }
        )
    for s, e, ordered in bullet_lines:
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": s, "endIndex": e + 1},
                    "bulletPreset": (
                        "NUMBERED_DECIMAL_NESTED" if ordered else "BULLET_DISC_CIRCLE_SQUARE"
                    ),
                }
            }
        )
    for s, e in bold_ranges:
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": s, "endIndex": e},
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            }
        )
    for s, e, url in link_ranges:
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": s, "endIndex": e},
                    "textStyle": {"link": {"url": url}},
                    "fields": "link",
                }
            }
        )
    return text, requests


def main() -> int:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    env = read_env_values(env_file)

    parser = argparse.ArgumentParser(
        description="Publish markdown test plan to Google Docs with formatting."
    )
    parser.add_argument("--title", required=True, help="Google Docs title.")
    parser.add_argument(
        "--markdown-file",
        default=None,
        help="Path to markdown input file. If omitted, read from stdin.",
    )
    parser.add_argument(
        "--auth-file",
        default=None,
        help="OAuth client file path. Defaults to OAUTH_FILE_PATH in .env.",
    )
    parser.add_argument(
        "--token-file",
        default=None,
        help="Token JSON path. Defaults to <auth-file>.token.json.",
    )
    parser.add_argument(
        "--redirect-port",
        type=int,
        default=None,
        help="OAuth callback port. Defaults to OAUTH_REDIRECT_PORT in .env or 8080.",
    )
    args = parser.parse_args()

    auth_path = args.auth_file or env.get("OAUTH_FILE_PATH")
    if not auth_path:
        raise RuntimeError("Missing OAuth auth path. Set OAUTH_FILE_PATH or pass --auth-file.")
    auth_file = Path(auth_path).expanduser().resolve()
    if not auth_file.exists():
        raise FileNotFoundError(f"Missing auth file: {auth_file}")

    token_file = (
        Path(args.token_file).expanduser().resolve()
        if args.token_file
        else auth_file.with_suffix(".token.json")
    )
    redirect_port = args.redirect_port or int(env.get("OAUTH_REDIRECT_PORT", "8080"))

    if args.markdown_file:
        markdown_text = Path(args.markdown_file).expanduser().resolve().read_text(encoding="utf-8")
    else:
        import sys

        markdown_text = sys.stdin.read()
    if not markdown_text.strip():
        raise RuntimeError("Input markdown is empty.")

    creds = load_credentials(auth_file, token_file, redirect_port)
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    _, requests = build_doc_requests(markdown_text.splitlines())
    file_result = drive.files().create(
        body={"name": args.title, "mimeType": "application/vnd.google-apps.document"},
        fields="id",
    ).execute()
    doc_id = file_result["id"]

    docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    print(f"https://docs.google.com/document/d/{doc_id}/edit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
