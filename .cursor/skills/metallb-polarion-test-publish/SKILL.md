---
name: metallb-polarion-test-publish
description: Publish MetalLB (or CNF) manual test cases to Polarion with testcase work items and a LiveDoc home page that embeds full descriptions and Step/Expected Result tables—not only work-item macros.
---

# MetalLB / Polarion testcase + LiveDoc publish

## When to use

The user wants **Polarion test cases** and/or a **LiveDoc module** listing manual tests (often from a detailed test plan tied to a Jira Epic).

**QE lifecycle:** In the standard four-phase flow (`references/metallb-qe-lifecycle-reference.mdc`), Polarion publish happens in **Phase 2** **after** the user **approves** the **detailed** Google Doc—not immediately after generating a draft detailed plan. If the user only asked for a detailed Doc and has not approved it, **do not** publish to Polarion yet.

## Non-negotiable behavior

After attaching testcase work items to a LiveDoc module, **always PATCH `homePageContent`** so the document itself shows:

- Document title and Contents (traceability **once per testcase** under that test — not at document top)
- Contents list
- Per testcase: title, link to WI, **Description**, **Setup**, **Test steps** as a **two-column table** (Step | Expected Result), **Teardown**
- Per testcase: **one `module-workitem` macro** (marks the WI in the document — without it Polarion shows "unmarked in the Document") plus readable inline HTML and a portal link. **No** trailing "Linked Polarion test cases" footer. **`validate_livedoc_home_html_policy`** requires exactly one macro per `work_item_id`, forbids **`<h1>`–`<h6>`**, and forbids the linked-section footer.

Do **not** leave the home page as only macro placeholders (the body must be readable HTML). Learn from **CNF MetalLB**: macros keep the outline flat, but we keep **inline readable HTML** instead—using **bold `<p>` labels only** so Polarion does not create extra Heading outline nodes. **One testcase work item ID per test**; no heading-derived IDs for Traceability, Purpose, Contents, etc.

**Test steps — Expected Result (non-negotiable):** For every epic `steps` tuple `(step_text, expected_text)`, set `expected_text` with **`expected_sample_output(verify_command, sample_text)`** from `adapters/polarion_test_publish.py`. The expected cell must contain a **`Run: oc …`** verification command and a **`Sample output:`** block with representative terminal output (tables, jsonpath lines, log snippets). Do **not** use prose-only expectations ("resource should be created", "status is Valid"). When building the epic module from an approved detailed Google Doc, copy the same **Run + Sample output** shape from each step’s **Expected** block (`metallb-detailed-test-plan` skill / `assets/template.md`).

## Testcase work-item metadata (mandatory on create)

Every testcase work item must set Polarion classification fields at upload time (reference: [OCP-86293](https://polarion.engineering.redhat.com/polarion/#/project/OSE/workitem?id=OCP-86293)). The publish pipeline applies these via `create_testcase(..., metadata=...)`. **Do not** set `level`, `component`, or `importance` — those REST keys do not populate the UI; use the `case*` attributes below.

**Hardcoded for MetalLB / CNF epics** (`CNF_METALLB_TESTCASE_METADATA_DEFAULTS` in `adapters/polarion_test_publish.py`):

| UI label | Polarion attribute | Value |
|----------|-------------------|-------|
| Level | `caselevel` | `component` |
| Component | `casecomponent` | `telco` |
| Subcomponent | `subcomponent` | `cnfnetwork` |
| Sub Team | `subteam` | `kni` |
| Products | `products` | `ocp` |
| Test type | `testtype` | `functional` |
| Automation | `caseautomation` | `notautomated` |
| Upstream | `upstream` | `no` |

**Per testcase** (required in each epic `test_definitions()` entry):

| Field | How to set |
|-------|------------|
| Pos/Neg | `caseposneg`: `positive` or `negative` (from epic `posneg` Positive/Negative) |
| Importance | `caseimportance`: `critical` / `high` / `medium` / `low` (also sets `priority`) |

Optional per-test overrides: `metadata` dict on the testcase entry. Epic-level override: `DEFAULT_TESTCASE_METADATA` on the epic module (non-CNF epics only).

## Code to reuse

| Piece | Role |
|-------|------|
| `adapters.polarion_adapter.html_section_label` | Bold `<p>` section titles (no `<h1>`–`<h6>` outline nodes) |
| `adapters/polarion_livedoc.build_livedoc_home_html` | Build standard HTML from `tests` dicts + `work_item_ids` (runs policy validation before return) |
| `adapters/polarion_livedoc.validate_livedoc_home_html_policy` | Call before `update_document_home_page` if HTML was not built by `build_livedoc_home_html` |
| `PolarionAdapter.publish_livedoc_home_page` | Build + PATCH in one call |
| `adapters.polarion_test_publish.expected_sample_output` | Expected Result cell: `Run: <verify cmd>` + `Sample output:` block |
| `adapters/polarion_test_publish.build_testcase_metadata` / `resolve_testcase_metadata` | Merge hardcoded + per-test Pos/Neg and Importance |
| `adapters.polarion_adapter.build_livedoc_portal_url` | Browser LiveDoc URL: `#/project/{project}/wiki/{space}/{module}` (not `/space/.../module/...`) |
| `PolarionAdapter.livedoc_portal_url` | Same URL for the adapter's project id |
| `PolarionAdapter.create_testcase`, `update_testcase_metadata`, `add_test_steps`, `move_workitem_to_document`, `create_module_document` | Create flow |
| `scripts/publish_polarion_livedoc_tests.py` | Generic publisher (`--epic-module <import.path>`; set `PYTHONPATH` if the module lives outside the repo root) |
| `examples/polarion_livedoc_epic_module/sample_epic.py` | Neutral template: `default_traceability()`, `test_definitions()`, optional `REPLACE_STALE_WORK_ITEMS` |

Each testcase dict must include: `title`, **`purpose`**, **`pass_fail`**, `setup_html`, `teardown_html`, `steps` as `list[tuple[str, str]]`, plus **`posneg`** and **`importance`**. Do **not** put Purpose/Pass-fail on the work item Description (empty WI Description avoids LiveDoc macro duplication).

**Expected Result column:** use `expected_sample_output(verify_command, sample_text)` for the second tuple element whenever a step changes or queries cluster state — include a **verification command** (`oc get` / `kubectl get`) and **representative terminal output**, not only prose like "resource should be created".

## Polarion quirks

See `references/metallb-polarion-livedoc-workflow.mdc`: `polarion_1` first, **no `<h1>`–`<h6>` anywhere**, use `html_section_label` for all titles/subsections (Description field included).

**Wrapping:** Step / Expected Result cells use a styled `<div>` (`pre-wrap` + `break-word`), not `<pre>`; LiveDoc tables use `table-layout:fixed` and 50% column width. Refresh existing WIs + wiki: `--home-page-only --attach-work-items … --resync-steps-and-home`.

## Space / location

For CNF epics, prefer LiveDoc space **`CNF`** (alongside **CNF MetalLB**). Override with `POLARION_SPACE_ID` or `--space-id`.

## LiveDoc browser URL

After publish, share the **wiki** route from `build_livedoc_portal_url(base, project_id, space_id, module_name)` or the URL printed by `scripts/publish_polarion_livedoc_tests.py`. Example:

`https://polarion.engineering.redhat.com/polarion/#/project/OSE/wiki/CNF/CNF_20333_MetalLB_ConfigurationState`

Do **not** link `#/project/.../space/.../module/...` — that SPA path redirects to the Polarion home page. REST `target_document` (`OSE/CNF/module_name`) is for APIs only, not browser navigation.

## Refresh home page only

If work items already exist:

`PYTHONPATH=examples python3 scripts/publish_polarion_livedoc_tests.py --epic-module polarion_livedoc_epic_module.sample_epic --home-page-only --attach-work-items <ids in TC order>`

For a real Epic, point `--epic-module` at your own package (or set `POLARION_EPIC_MODULE`) and supply traceability from **user-provided data**:

- **Preferred:** `POLARION_TRACE_EPIC_URL`, `POLARION_TRACE_EPIC_LABEL`, `POLARION_TRACE_HIGH_LEVEL_PLAN_URL`, `POLARION_TRACE_DETAILED_PLAN_URL` in `.env` or **shell `export`** (shell wins over `.env` for these keys).
- **Convenience:** if the user only gives an Epic key and Doc URLs, set `METALLB_JIRA_EPIC_KEY` and optionally `METALLB_HIGH_LEVEL_PLAN_URL` / `METALLB_DETAILED_PLAN_URL` when the corresponding `POLARION_TRACE_*` variables are **not** set. CLI flags `--epic-url`, `--epic-label`, etc. still override after env merge.
- **Epic module:** testcase bodies remain in Python (`test_definitions`); traceability strings can be fully driven by env as above.

Alternatively call `publish_livedoc_home_page` with the same testcase dict shape.
