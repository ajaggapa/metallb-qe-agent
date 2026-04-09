# Agent Guardrails for Test Plan Generation

These rules are mandatory when fulfilling requests like "create a high level test plan" or "create a detailed test plan" for MetalLB EPICs.

## QE lifecycle (four phases, user gates)

Feature Epics follow **Phase 1 → 2 → 3 → 4** with a **mandatory user validation** before moving to the next phase. Full behavior is in `.cursor/rules/metallb-qe-lifecycle.mdc`.

1. **High-level test plan** — Google Doc; peer QE + developer review; user approves before Phase 2.
2. **Detailed test plan** — From approved high-level Doc; optional `KUBECONFIG` for hands-on validation of every TC on a test cluster; OCPBUGS + **Networking / Metal LB** for confirmed bugs; user approves Doc; then **Polarion** LiveDoc under **`CNF`** (unless user overrides space).
3. **First execution** — User supplies Polarion testcase IDs + `KUBECONFIG` (prefer another cluster); agent runs procedures and reports a **results table**; user approves before Phase 4.
4. **Test automation** — User’s **GitHub fork**: test branch, `e2etest/` changes, push and rely on **user repo GitHub Actions**; **do not open a PR** unless the user explicitly asks.

Skills: `metallb-high-level-test-plan`, `metallb-detailed-test-plan`, `metallb-polarion-test-publish`, `metallb-manual-test-execution`, `metallb-e2e-automation`.

## Mandatory Output Path

- Final artifact must be a formatted Google Doc.
- Return only the Google Docs URL unless the user explicitly asks for local files.
- Do not persist test plan markdown files in the project workspace.

## Mandatory Publish Pipeline

### High-level test plan

1. Generate markdown content in memory or transient file under `/tmp`.
2. Validate and publish using:
   - `scripts/validate_and_publish_test_plan.sh "High-Level Test Plan - <JIRA_KEY> - <Feature Name>"`
   - Provide markdown content via stdin.
3. Do not use `adapters/google_docs_adapter.py` or other ad-hoc Docs upload paths for final output.

### Detailed test plan (YAML + oc/kubectl)

1. Follow `.cursor/skills/metallb-detailed-test-plan/SKILL.md` and its `template.md`.
2. Generate markdown in memory or under `/tmp` only.
3. Validate and publish using:
   - `scripts/validate_and_publish_detailed_test_plan.sh "Detailed Test Plan - <JIRA_KEY> - <Feature Name>"`
   - Provide markdown content via stdin.
4. Each test case must include copy-paste YAML fences and `oc`/`kubectl` commands per validated structure.

## Repository Analysis Location

- Clone/update analysis repos only under:
  - `.cursor/workspaces/metallb-repo-analysis/`
- Repos:
  - `metallb-operator`
  - `metallb`
  - `frr-k8s`

## Formatting Expectations

- Google Doc must include:
  - Title style
  - Section headings
  - Bold inline labels in test cases (`Purpose`, `Procedure`, `Expected Result`, `Pass/Fail Criteria`)
  - Proper bullet/numbered lists
  - Clickable links in `References`

### Detailed test plans (extra)

- Hardcode MetalLB namespace `metallb-system` in YAML and `oc`/`kubectl` commands unless the Epic explicitly names a different namespace (state that exception once under Prerequisites).
- Do not use ALL_CAPS substitution variables (`METALLB_NS`, `TEST_POOL_NAME`, etc.); use concrete object names and literal CIDRs, and derive per-node names in `bash` when needed (see `.cursor/skills/metallb-detailed-test-plan/SKILL.md`).
- Keep Google Docs output readable: no “reference only” YAML blocks, no prose crammed inside fenced YAML, and use plain (non-bold) labels for `Manifest (YAML):`, `Run:`, and `Expected:`; keep `**Purpose:**` for validator compatibility.
- In `## Placeholders`, use **grouped bullet lists** (Namespace / Baseline / test objects), not markdown tables—tables often paste as unusable plain text in Docs.

## Polarion testcase + LiveDoc (when the deliverable is Polarion)

When the user asks for **Polarion** test cases / LiveDoc modules (not only Google Docs):

1. Follow `.cursor/rules/metallb-polarion-livedoc-workflow.mdc` and skill `.cursor/skills/metallb-polarion-test-publish/SKILL.md`.
2. **Mandatory:** after creating testcase work items and moving them into the module, call **`PolarionAdapter.publish_livedoc_home_page`** (or `build_livedoc_home_html` + `update_document_home_page`) so the **module home page HTML** includes full **Description**, **Setup**, **Step | Expected Result** tables, **Teardown**, and a **link to each testcase** under its title. **`build_livedoc_home_html` raises `ValueError`** if the output would include a "Linked Polarion test cases" section or `module-workitem` macros; do not ship a document that is only macro placeholders. If you PATCH custom HTML with `update_document_home_page`, run **`validate_livedoc_home_html_policy`** first unless you have an explicit, documented exception.
3. Reuse `adapters/polarion_livedoc.py` and `adapters/polarion_adapter.py`; use `scripts/publish_cnf20333_polarion_tests.py` as the reference flow for CNF-20333-style epics.
