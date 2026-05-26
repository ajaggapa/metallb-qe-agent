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

- Document title and traceability (Epic, high-level plan links)
- Contents list
- Per testcase: title, link to WI, **Description**, **Setup**, **Test steps** as a **two-column table** (Step | Expected Result), **Teardown**
- Per testcase: link to the Polarion work item (portal URL) under the title—**no** extra "Linked Polarion test cases" / macro footer. **`build_livedoc_home_html` enforces this** via `validate_livedoc_home_html_policy` (`ValueError` if `module-workitem` or that section title appears anywhere in the assembled HTML).

Do **not** leave the home page as only macro placeholders (the body must be readable HTML).

## Code to reuse

| Piece | Role |
|-------|------|
| `adapters/polarion_livedoc.build_livedoc_home_html` | Build standard HTML from `tests` dicts + `work_item_ids` (runs policy validation before return) |
| `adapters/polarion_livedoc.validate_livedoc_home_html_policy` | Call before `update_document_home_page` if HTML was not built by `build_livedoc_home_html` |
| `PolarionAdapter.publish_livedoc_home_page` | Build + PATCH in one call |
| `PolarionAdapter.create_testcase`, `add_test_steps`, `move_workitem_to_document`, `create_module_document` | Create flow |
| `scripts/publish_polarion_livedoc_tests.py` | Generic publisher (`--epic-module <import.path>`; set `PYTHONPATH` if the module lives outside the repo root) |
| `examples/polarion_livedoc_epic_module/sample_epic.py` | Neutral template: `default_traceability()`, `test_definitions()`, optional `REPLACE_STALE_WORK_ITEMS` |

Each testcase dict must include: `title`, `description_html`, `setup_html`, `teardown_html`, `steps` as `list[tuple[str, str]]`.

## Polarion quirks

See `references/metallb-polarion-livedoc-workflow.mdc`: `polarion_1` first, no custom heading `id=`, avoid `<h3>` for subsection labels.

**Wrapping:** Step / Expected Result cells use a styled `<div>` (`pre-wrap` + `break-word`), not `<pre>`; LiveDoc tables use `table-layout:fixed` and 50% column width. Refresh existing WIs + wiki: `--home-page-only --attach-work-items … --resync-steps-and-home`.

## Space / location

For CNF epics, prefer LiveDoc space **`CNF`** (alongside **CNF MetalLB**). Override with `POLARION_SPACE_ID` or `--space-id`.

## Refresh home page only

If work items already exist:

`PYTHONPATH=examples python3 scripts/publish_polarion_livedoc_tests.py --epic-module polarion_livedoc_epic_module.sample_epic --home-page-only --attach-work-items <ids in TC order>`

For a real Epic, point `--epic-module` at your own package (or set `POLARION_EPIC_MODULE`) and supply traceability from **user-provided data**:

- **Preferred:** `POLARION_TRACE_EPIC_URL`, `POLARION_TRACE_EPIC_LABEL`, `POLARION_TRACE_HIGH_LEVEL_PLAN_URL`, `POLARION_TRACE_DETAILED_PLAN_URL` in `.env` or **shell `export`** (shell wins over `.env` for these keys).
- **Convenience:** if the user only gives an Epic key and Doc URLs, set `METALLB_JIRA_EPIC_KEY` and optionally `METALLB_HIGH_LEVEL_PLAN_URL` / `METALLB_DETAILED_PLAN_URL` when the corresponding `POLARION_TRACE_*` variables are **not** set. CLI flags `--epic-url`, `--epic-label`, etc. still override after env merge.
- **Epic module:** testcase bodies remain in Python (`test_definitions`); traceability strings can be fully driven by env as above.

Alternatively call `publish_livedoc_home_page` with the same testcase dict shape.
