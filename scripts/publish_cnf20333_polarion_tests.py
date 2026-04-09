#!/usr/bin/env python3
"""
Create Polarion LiveDoc module + testcase work items for Epic CNF-20333 (MetalLB ConfigurationState).

Prerequisites:
  pip install polarion-rest-client
  .env: POLARION_BASE_URL, POLARION_PROJECT_ID, POLARION_TOKEN
  Optional: POLARION_SPACE_ID (default: CNF — same wiki area as OSE/wiki/CNF/CNF MetalLB)

Usage:
  python3 scripts/publish_cnf20333_polarion_tests.py
  python3 scripts/publish_cnf20333_polarion_tests.py --dry-run
  python3 scripts/publish_cnf20333_polarion_tests.py --module-name CNF_20333_MyDoc
  python3 scripts/publish_cnf20333_polarion_tests.py --delete-work-items OCP-88582,OCP-88583

After publish, the LiveDoc home page is PATCHed with full HTML: titles, Description, Setup,
Step | Expected Result tables, Teardown, and per-testcase Polarion links (no trailing "Linked test cases" section).

Refresh an existing doc body only:
  python3 scripts/publish_cnf20333_polarion_tests.py --home-page-only \\
    --attach-work-items OCP-88586,OCP-88587,OCP-88588,OCP-88589

Refresh LiveDoc table + replace testcase Test Steps (word-wrapped cells):
  python3 scripts/publish_cnf20333_polarion_tests.py --home-page-only \\
    --attach-work-items OCP-88586,OCP-88587,OCP-88588,OCP-88589 --resync-steps-and-home
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters.polarion_adapter import (  # noqa: E402
    PolarionAdapter,
    html_paragraph,
    read_env_values,
)

HIGH_LEVEL_PLAN_URL = (
    "https://docs.google.com/document/d/1IuVwODz84KJwE3ksLuc2_7tKiwPnXYlfaTsBM1RRMiA/"
    "edit?tab=t.0#heading=h.mij3i2qufkg9"
)
EPIC_URL = "https://redhat.atlassian.net/browse/CNF-20333"


def _desc(purpose: str, pass_fail: str) -> str:
    return (
        "<h4>Traceability</h4>"
        f"<ul>"
        f"<li>Epic: <a href=\"{EPIC_URL}\">CNF-20333</a></li>"
        f"<li>High-level test plan: <a href=\"{HIGH_LEVEL_PLAN_URL}\">Google Doc</a></li>"
        f"</ul>"
        "<h4>Purpose</h4>"
        f"{html_paragraph(purpose)}"
        "<h4>Pass / fail (summary)</h4>"
        f"{html_paragraph(pass_fail)}"
    )


# Baseline setup shared across cases (namespace metallb-system, concrete object names per detailed plan).
COMMON_SETUP = """<ul>
<li>OpenShift or Kubernetes cluster with MetalLB installed (FRR or frr-k8s mode).</li>
<li>CRD <code>configurationstates.metallb.io</code> present.</li>
<li>MetalLB running in namespace <code>metallb-system</code>; controller and speaker pods Ready.</li>
<li>CLI: <code>oc</code> logged in with permissions to create/delete CRs in <code>metallb-system</code>.</li>
</ul>"""


def test_definitions():
    """Aligned to the detailed manual plan for CNF-20333 / ConfigurationState API."""
    return [
        {
            "title": "[CNF-20333] TC-01 Observe valid ConfigurationState for controller and speakers",
            "description_html": _desc(
                "Confirm that after a healthy MetalLB deployment, one ConfigurationState exists for "
                "the controller and one per speaker node, each with status Valid and no error summary.",
                "CRD exists; oc get configurationstates shows controller and speaker-<node> rows with "
                "Valid; describe shows no configuration error summary for healthy configs.",
            ),
            "setup_html": COMMON_SETUP,
            "teardown_html": (
                "<p>Optional cleanup (if baseline pool was applied):</p>"
                "<pre>"
                "oc delete ipaddresspool cnf20333-baseline-pool -n metallb-system --ignore-not-found\n"
                "oc delete l2advertisement cnf20333-baseline-l2 -n metallb-system --ignore-not-found"
                "</pre>"
            ),
            "steps": [
                (
                    "Run:\n"
                    "oc get crd configurationstates.metallb.io -o name",
                    "Output includes customresourcedefinition.apiextensions.k8s.io/configurationstates.metallb.io",
                ),
                (
                    (
                        "Apply optional baseline (save as YAML). IPAddressPool cnf20333-baseline-pool "
                        "with addresses 192.0.2.0/24 and L2Advertisement cnf20333-baseline-l2 referencing "
                        "that pool, both in namespace metallb-system. Then run:\n"
                        "oc apply -f baseline.yaml\n"
                        "oc wait --for=condition=Ready pod -l app.kubernetes.io/component=speaker "
                        "-n metallb-system --timeout=120s || true\n"
                        "oc get configurationstates -n metallb-system"
                    ),
                    "Apply succeeds; list shows controller and one speaker-<node> per speaker; "
                    "Result column shows Valid where printed.",
                ),
                (
                    "Run:\n"
                    "oc get configurationstates -n metallb-system -l metallb.io/component-type=controller\n"
                    "oc get configurationstates -n metallb-system -l metallb.io/component-type=speaker\n"
                    "NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker "
                    "-o jsonpath='{.items[0].spec.nodeName}')\n"
                    "oc describe configurationstate controller -n metallb-system\n"
                    "oc describe configurationstate \"speaker-${NODE}\" -n metallb-system",
                    "Label filters return expected rows; describe shows Valid and no error summary.",
                ),
            ],
        },
        {
            "title": "[CNF-20333] TC-02 Speaker Invalid when BGPPeer references missing BFD profile",
            "description_html": _desc(
                "Verify transient-reference errors appear on the speaker ConfigurationState "
                "(not only in pod logs).",
                "After BGPPeer without BFD profile: status.result Invalid and errorSummary mentions missing "
                "BFD profile; after creating BFDProfile, status returns to Valid.",
            ),
            "setup_html": COMMON_SETUP,
            "teardown_html": (
                "<pre>"
                "oc delete bgppeer cnf20333-peer-bfd-missing -n metallb-system --ignore-not-found\n"
                "oc delete bfdprofile cnf20333-bfd-profile -n metallb-system --ignore-not-found"
                "</pre>"
            ),
            "steps": [
                (
                    "Apply BGPPeer cnf20333-peer-bfd-missing in metallb-system: myASN 64512, peerASN 64513, "
                    "peerAddress 198.51.100.1, bfdProfile cnf20333-bfd-profile (profile not created yet).",
                    "oc apply succeeds; BGPPeer resource is created.",
                ),
                (
                    "Run:\n"
                    "NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker "
                    "-o jsonpath='{.items[0].spec.nodeName}')\n"
                    "oc get configurationstate \"speaker-${NODE}\" -n metallb-system "
                    "-o jsonpath='{.status.result}{\"\\n\"}{.status.errorSummary}{\"\\n\"}'",
                    "status.result is Invalid; errorSummary indicates missing BFD profile (wording may vary by build).",
                ),
                (
                    "Create BFDProfile cnf20333-bfd-profile in metallb-system (empty spec). Then re-check "
                    "ConfigurationState for the same NODE after a short wait.",
                    "status.result becomes Valid; errorSummary empty.",
                ),
            ],
        },
        {
            "title": "[CNF-20333] TC-03 Speaker Invalid when BGP password Secret has wrong type",
            "description_html": _desc(
                "Confirm reconciler-side validation of password Secret surfaces on speaker ConfigurationState.",
                "With Opaque secret: Invalid and type mismatch message; after kubernetes.io/basic-auth secret: Valid.",
            ),
            "setup_html": COMMON_SETUP,
            "teardown_html": (
                "<pre>"
                "oc delete bgppeer cnf20333-peer-bad-secret -n metallb-system --ignore-not-found\n"
                "oc delete secret cnf20333-bgp-password -n metallb-system --ignore-not-found"
                "</pre>"
            ),
            "steps": [
                (
                    "Create Secret cnf20333-bgp-password (type Opaque) and BGPPeer cnf20333-peer-bad-secret "
                    "in metallb-system referencing that secret (peerAddress 198.51.100.2, ASNs 64512/64513).",
                    "Secret and BGPPeer create successfully.",
                ),
                (
                    "Run:\n"
                    "NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker "
                    "-o jsonpath='{.items[0].spec.nodeName}')\n"
                    "oc get configurationstate \"speaker-${NODE}\" -n metallb-system "
                    "-o jsonpath='{.status.result}{\"\\n\"}{.status.errorSummary}{\"\\n\"}'",
                    "Invalid; errorSummary mentions secret type mismatch / expected kubernetes.io/basic-auth.",
                ),
                (
                    "Delete the secret; recreate cnf20333-bgp-password as type kubernetes.io/basic-auth "
                    "with stringData.password. Wait and re-check status.result.",
                    "status.result becomes Valid.",
                ),
            ],
        },
        {
            "title": "[CNF-20333] TC-04 Deleted speaker ConfigurationState is recreated and returns Valid",
            "description_html": _desc(
                "Ensure ConfigurationStateReconciler recreates a deleted speaker ConfigurationState.",
                "After oc delete configurationstate speaker-<node>, object reappears and status.result returns Valid.",
            ),
            "setup_html": COMMON_SETUP,
            "teardown_html": (
                "<pre>"
                "oc delete configmap cnf20333-configstate-removal-marker -n metallb-system --ignore-not-found"
                "</pre>"
            ),
            "steps": [
                (
                    "Optional marker:\n"
                    "oc apply -f- <<EOF\n"
                    "apiVersion: v1\n"
                    "kind: ConfigMap\n"
                    "metadata:\n"
                    "  name: cnf20333-configstate-removal-marker\n"
                    "  namespace: metallb-system\n"
                    "data:\n"
                    "  purpose: tc-04-setup\n"
                    "EOF\n"
                    "NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker "
                    "-o jsonpath='{.items[0].spec.nodeName}')\n"
                    "oc get configurationstate \"speaker-${NODE}\" -n metallb-system "
                    "-o jsonpath='{.status.result}{\"\\n\"}'",
                    "ConfigMap applies; current result is Valid (wait for steady cluster if needed).",
                ),
                (
                    "Run:\n"
                    "NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker "
                    "-o jsonpath='{.items[0].spec.nodeName}')\n"
                    "oc delete configurationstate \"speaker-${NODE}\" -n metallb-system --wait=true\n"
                    "oc get configurationstate \"speaker-${NODE}\" -n metallb-system -o name",
                    "Delete succeeds; same ConfigurationState name appears again shortly.",
                ),
                (
                    "Poll until Valid:\n"
                    "NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker "
                    "-o jsonpath='{.items[0].spec.nodeName}')\n"
                    "for i in $(seq 1 24); do\n"
                    "  r=$(oc get configurationstate \"speaker-${NODE}\" -n metallb-system "
                    "-o jsonpath='{.status.result}' 2>/dev/null || echo \"\")\n"
                    "  echo \"attempt $i result=$r\"\n"
                    "  [ \"$r\" = \"Valid\" ] && exit 0\n"
                    "  sleep 5\n"
                    "done\n"
                    "exit 1",
                    "Loop exits 0 with Valid within the wait window.",
                ),
            ],
        },
    ]


DOC_H1_TITLE = "CNF-20333 MetalLB ConfigurationState — manual tests"


def _traceability_html() -> str:
    return (
        "<p><strong>Epic:</strong> "
        f'<a href="{EPIC_URL}">CNF-20333</a> — '
        "<strong>High-level plan:</strong> "
        f'<a href="{HIGH_LEVEL_PLAN_URL}">Google Doc</a>.</p>'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish CNF-20333 Polarion testcases.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not call Polarion.",
    )
    parser.add_argument(
        "--space-id",
        default=None,
        help="Polarion space id (default: env POLARION_SPACE_ID or CNF, alongside CNF MetalLB).",
    )
    parser.add_argument(
        "--module-name",
        default=None,
        help="New LiveDoc module name (default: CNF_20333_MetalLB_ConfigurationState_Manual).",
    )
    parser.add_argument(
        "--delete-work-items",
        default=None,
        metavar="IDS",
        help="Comma-separated short work item ids to delete before publishing (e.g. migration from wrong space).",
    )
    parser.add_argument(
        "--skip-document-create",
        action="store_true",
        help="Do not POST a new LiveDoc; only create test cases and move them to --module-name in --space-id.",
    )
    parser.add_argument(
        "--home-page-only",
        action="store_true",
        help="Only PATCH the LiveDoc home page HTML (use with --attach-work-items).",
    )
    parser.add_argument(
        "--attach-work-items",
        default=None,
        metavar="IDS",
        help="Comma-separated work item ids in TC-01..TC-04 order (for --home-page-only).",
    )
    parser.add_argument(
        "--resync-steps-and-home",
        action="store_true",
        help="With --home-page-only: delete/recreate each testcase's Test Steps (wrapped HTML) and PATCH LiveDoc home.",
    )
    args = parser.parse_args()

    env_file = ROOT / ".env"
    env = read_env_values(env_file)
    base = env.get("POLARION_BASE_URL")
    proj = env.get("POLARION_PROJECT_ID")
    token = env.get("POLARION_TOKEN")
    space = args.space_id or env.get("POLARION_SPACE_ID") or "CNF"
    module_name = args.module_name or "CNF_20333_MetalLB_ConfigurationState_Manual"

    if not all([base, proj, token]):
        print("Missing POLARION_BASE_URL, POLARION_PROJECT_ID, or POLARION_TOKEN in .env", file=sys.stderr)
        return 2

    title_doc = "CNF-20333 MetalLB ConfigurationState — manual tests"
    target_document = f"{proj}/{space}/{module_name}"
    tests = test_definitions()

    if args.dry_run:
        print("Dry run — would create:")
        if args.delete_work_items:
            print(f"  Delete work items: {args.delete_work_items}")
        if args.home_page_only:
            print("  Home page only: PATCH embedded HTML (no macro footer)")
            if args.attach_work_items:
                print(f"  Work items: {args.attach_work_items}")
            if args.resync_steps_and_home:
                print("  Resync: replace testcase Test Steps + home page (wrapped table cells)")
        if not args.skip_document_create and not args.home_page_only:
            print(f"  Document: {target_document}")
            print(f"  Title: {title_doc}")
        elif args.skip_document_create and not args.home_page_only:
            print(f"  Skip document create; target: {target_document}")
        for t in tests:
            print(f"  - {t['title']} ({len(t['steps'])} steps)")
        if not args.home_page_only:
            print("  Then: PATCH LiveDoc home page with full HTML (titles, steps tables).")
        return 0

    adapter = PolarionAdapter(base_url=base, project_id=proj, token=token)

    if args.home_page_only:
        if not args.attach_work_items:
            print("--home-page-only requires --attach-work-items OCP-1,OCP-2,...", file=sys.stderr)
            return 2
        ids = [x.strip() for x in args.attach_work_items.split(",") if x.strip()]
        if len(ids) != len(tests):
            print(
                f"Expected {len(tests)} work item ids (TC order), got {len(ids)}",
                file=sys.stderr,
            )
            return 2
        if args.resync_steps_and_home:
            for tc, wid in zip(tests, ids, strict=True):
                print(f"Replacing Polarion Test Steps for {wid} …")
                adapter.replace_test_steps(wid, tc["steps"])
        adapter.publish_livedoc_home_page(
            space,
            module_name,
            document_h1_title=DOC_H1_TITLE,
            traceability_html=_traceability_html(),
            tests=tests,
            work_item_ids=ids,
        )
        print("Updated LiveDoc home page:", target_document)
        return 0

    if args.delete_work_items:
        to_del = [x.strip() for x in args.delete_work_items.split(",") if x.strip()]
        if to_del:
            print("Deleting work items:", ", ".join(to_del))
            adapter.delete_work_items(to_del)

    if args.skip_document_create:
        print("Skipping document create; using existing module:", target_document)
    else:
        doc = adapter.create_module_document(
            space,
            module_name,
            title=title_doc,
        )
        print("Created document:", doc.get("id", doc))

    created_ids: list[str] = []
    for tc in tests:
        wid = adapter.create_testcase(
            title=tc["title"],
            description_html=tc["description_html"],
            setup_html=tc["setup_html"],
            teardown_html=tc["teardown_html"],
            status="draft",
        )
        adapter.add_test_steps(wid, tc["steps"])
        adapter.move_workitem_to_document(wid, target_document=target_document)
        portal = f"{base.rstrip('/')}/polarion/redirect/project/{proj}/workitem?id={wid}"
        print(f"Created & attached {wid}: {tc['title']}")
        print(f"  {portal}")
        created_ids.append(wid)

    adapter.publish_livedoc_home_page(
        space,
        module_name,
        document_h1_title=DOC_H1_TITLE,
        traceability_html=_traceability_html(),
        tests=tests,
        work_item_ids=created_ids,
    )
    print("\nUpdated LiveDoc home page with embedded descriptions and test-step tables.")

    print("\nDone.")
    print(f"Document module: {target_document}")
    print(f"Test case IDs: {', '.join(created_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
