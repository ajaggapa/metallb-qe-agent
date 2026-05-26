#!/usr/bin/env python3
"""Create Google Slides using OAuth credentials (Slides API).

Auth is **browser-based** (installed-app OAuth): ``InstalledAppFlow`` starts a
short-lived loopback server and opens your default browser to sign in with
Google. Use a GCP **Desktop** OAuth client JSON (same pattern as
``google_docs_adapter.py``). Add redirect URI ``http://127.0.0.1:<port>/`` (and
``http://localhost:<port>/`` if Google requires it) for the port you use
(default 8080, overridable with ``--port`` or ``OAUTH_REDIRECT_PORT``).
"""

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

SCOPES = ["https://www.googleapis.com/auth/presentations"]


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


def _load_credentials(
    auth_path: Path,
    token_path: Path,
    *,
    oauth_port: int,
    open_browser: bool,
):
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    if data.get("type") == "service_account":
        raise RuntimeError(
            f"Service account auth is disabled for '{auth_path.name}'. "
            "Use a Desktop OAuth client JSON and browser sign-in."
        )

    creds = None
    if token_path.exists():
        creds = UserCredentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(auth_path), SCOPES)
            print(
                "Browser OAuth: opening Google sign-in (Slides access).\n"
                f"  Loopback redirect: http://127.0.0.1:{oauth_port}/\n"
                "  If the browser does not open, use the URL printed below by the library.\n"
                "  GCP OAuth client type must be **Desktop**; enable **Google Slides API**.\n",
                flush=True,
            )
            creds = flow.run_local_server(
                port=oauth_port,
                open_browser=open_browser,
            )
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _delete_all_text(object_id: str) -> dict:
    return {
        "deleteText": {
            "objectId": object_id,
            "textRange": {"type": "ALL"},
        }
    }


def _shape_for_element_id(slide: dict, element_object_id: str) -> dict | None:
    for el in slide.get("pageElements", []):
        if el.get("objectId") == element_object_id:
            return el.get("shape")
    return None


def _shape_text_length(shape: dict | None) -> int:
    """Total length of text runs in a shape (0 if empty / no text)."""
    if not shape:
        return 0
    n = 0
    for te in shape.get("text", {}).get("textElements", []):
        tr = te.get("textRun")
        if tr and isinstance(tr.get("content"), str):
            n += len(tr["content"])
    return n


def _placeholder_map(slide: dict) -> dict[str, str]:
    """Map placeholder type (e.g. TITLE, BODY) to page element objectId."""
    out: dict[str, str] = {}
    for el in slide.get("pageElements", []):
        shape = el.get("shape")
        if not shape:
            continue
        ph = shape.get("placeholder")
        if not ph:
            continue
        t = ph.get("type")
        if t:
            out[t] = el["objectId"]
    return out


class GoogleSlidesAdapter:
    """Minimal Slides API wrapper using OAuth user credentials (browser flow)."""

    def __init__(
        self,
        auth_path: Path,
        token_path: Path,
        *,
        oauth_port: int | None = None,
        open_browser: bool = True,
    ):
        port = oauth_port if oauth_port is not None else int(os.getenv("OAUTH_REDIRECT_PORT", "8080"))
        self.credentials = _load_credentials(
            auth_path,
            token_path,
            oauth_port=port,
            open_browser=open_browser,
        )
        self.slides_service = build("slides", "v1", credentials=self.credentials)

    def create_presentation(self, title: str) -> str:
        pres = self.slides_service.presentations().create(body={"title": title}).execute()
        return pres["presentationId"]

    def batch_update(self, presentation_id: str, requests: list[dict]) -> None:
        if not requests:
            return
        self.slides_service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()

    def get_presentation(self, presentation_id: str) -> dict:
        return self.slides_service.presentations().get(presentationId=presentation_id).execute()


def build_metallb_ci_overview_slides(adapter: GoogleSlidesAdapter, presentation_id: str) -> None:
    """Populate deck: title slide + repo map + one slide per component + summary."""
    pres = adapter.get_presentation(presentation_id)
    first = pres["slides"][0]
    ph = _placeholder_map(first)

    requests: list[dict] = []
    if title_id := ph.get("CENTERED_TITLE") or ph.get("TITLE"):
        title_shape = _shape_for_element_id(first, title_id)
        if _shape_text_length(title_shape) > 0:
            requests.append(_delete_all_text(title_id))
        requests.append(
            {
                "insertText": {
                    "objectId": title_id,
                    "text": "MetalLB product & CI",
                    "insertionIndex": 0,
                }
            }
        )
    if sub_id := ph.get("SUBTITLE"):
        sub_shape = _shape_for_element_id(first, sub_id)
        if _shape_text_length(sub_shape) > 0:
            requests.append(_delete_all_text(sub_id))
        requests.append(
            {
                "insertText": {
                    "objectId": sub_id,
                    "text": "Upstream (any Kubernetes) vs downstream (OpenShift)",
                    "insertionIndex": 0,
                }
            }
        )

    slide_specs: list[tuple[str, str, str]] = [
        (
            "slide_repos",
            "Repositories (upstream / downstream)",
            "metallb-operator\n"
            "  upstream: https://github.com/metallb/metallb-operator\n"
            "  downstream: https://github.com/openshift/metallb-operator\n\n"
            "metallb\n"
            "  upstream: https://github.com/metallb/metallb\n"
            "  downstream: https://github.com/openshift/metallb\n\n"
            "frr-k8s\n"
            "  upstream: https://github.com/metallb/frr-k8s\n"
            "  downstream: https://github.com/openshift/frr",
        ),
        (
            "slide_operator",
            "metallb-operator — CI",
            "Upstream\n"
            "• GitHub Actions: e2e on KIND\n\n"
            "Downstream (OpenShift / RnD)\n"
            "• Pre-merge CI on every PR\n"
            "• No periodic CI today\n"
            "• Currently part of cnf-tests; proposal to remove from cnf-tests",
        ),
        (
            "slide_metallb",
            "metallb — CI",
            "Upstream\n"
            "• GitHub Actions: e2e on KIND\n\n"
            "Downstream (OpenShift / RnD)\n"
            "• Pre-merge CI on every PR\n"
            "• Periodic CI: OCP 4.21, 4.20, 4.19",
        ),
        (
            "slide_frr",
            "frr-k8s — CI",
            "Upstream\n"
            "• GitHub Actions: e2e on KIND\n\n"
            "Downstream (OpenShift / RnD)\n"
            "• Pre-merge CI on every PR\n"
            "• Periodic CI: OCP 4.21 through 4.18",
        ),
        (
            "slide_summary",
            "Summary",
            "• Upstream: portable Kubernetes; CI centered on KIND + GHA\n"
            "• Downstream: OpenShift-focused; PR gating + selective periodic coverage\n"
            "• Operator downstream: periodic gap; cnf-tests coupling under review",
        ),
    ]

    for sid, _, _ in slide_specs:
        requests.append(
            {
                "createSlide": {
                    "objectId": sid,
                    "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                }
            }
        )

    adapter.batch_update(presentation_id, requests)

    pres2 = adapter.get_presentation(presentation_id)
    slide_by_id = {s["objectId"]: s for s in pres2["slides"]}

    fill: list[dict] = []
    for sid, stitle, body in slide_specs:
        slide = slide_by_id.get(sid)
        if not slide:
            continue
        m = _placeholder_map(slide)
        if tid := m.get("TITLE"):
            tshape = _shape_for_element_id(slide, tid)
            if _shape_text_length(tshape) > 0:
                fill.append(_delete_all_text(tid))
            fill.append({"insertText": {"objectId": tid, "text": stitle, "insertionIndex": 0}})
        if bid := m.get("BODY"):
            bshape = _shape_for_element_id(slide, bid)
            if _shape_text_length(bshape) > 0:
                fill.append(_delete_all_text(bid))
            fill.append({"insertText": {"objectId": bid, "text": body, "insertionIndex": 0}})

    adapter.batch_update(presentation_id, fill)


def main() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    env_values = read_env_values(env_file)

    parser = argparse.ArgumentParser(
        description=(
            "Create a Google Slides deck (MetalLB CI overview) using "
            "browser-based OAuth (loopback + Google sign-in)."
        )
    )
    parser.add_argument(
        "--auth-file",
        default=None,
        help="OAuth client JSON path. Defaults to OAUTH_FILE_PATH in .env.",
    )
    parser.add_argument(
        "--token-file",
        default=None,
        help="Token JSON path. Defaults to <auth-file>.slides.token.json next to auth file.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Presentation title (default includes timestamp).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="OAuth loopback port (default: OAUTH_REDIRECT_PORT or 8080).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser; print the authorization URL only (rare).",
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
        else auth_file.with_name(auth_file.stem + ".slides.token.json")
    )

    oauth_port = args.port
    if oauth_port is None and env_values.get("OAUTH_REDIRECT_PORT"):
        oauth_port = int(env_values["OAUTH_REDIRECT_PORT"])
    adapter = GoogleSlidesAdapter(
        auth_file,
        token_file,
        oauth_port=oauth_port,
        open_browser=not args.no_browser,
    )
    title = args.title or f"MetalLB CI overview {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC"
    pid = adapter.create_presentation(title)
    build_metallb_ci_overview_slides(adapter, pid)
    url = f"https://docs.google.com/presentation/d/{pid}/edit"
    print(f"Created Google Slides: title={title!r}\n{url}")


if __name__ == "__main__":
    main()
