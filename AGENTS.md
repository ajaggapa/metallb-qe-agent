# Agent Guardrails for Test Plan Generation

These rules are mandatory when fulfilling requests like "create a high level test plan" or "create a detailed test plan" for MetalLB EPICs.

## QE lifecycle (four phases, user gates)

Feature Epics follow **Phase 1 → 2 → 3 → 4** with a **mandatory user validation** before moving to the next phase. Full behavior is in `.cursor/skills/metallb-detailed-test-plan/references/metallb-qe-lifecycle.mdc`.

1. **High-level test plan** — Agent returns draft in **chat** first; user publishes to Google Doc **only when they ask**; then peer QE + developer review; user approves before Phase 2.
2. **Detailed test plan** — From approved high-level Doc; optional `KUBECONFIG` for hands-on validation of every TC on a test cluster; OCPBUGS + **Networking / Metal LB** for confirmed bugs; user approves Doc; then **Polarion** LiveDoc under **`CNF`** (unless user overrides space).
3. **First execution** — User supplies Polarion testcase IDs + `KUBECONFIG` (prefer another cluster); agent runs procedures and reports a **results table**; user approves before Phase 4.
4. **Test automation** — User’s **GitHub fork**: test branch, `e2etest/` changes, push and rely on **user repo GitHub Actions**; **do not open a PR** unless the user explicitly asks.

Skills: `metallb-high-level-test-plan`, `metallb-detailed-test-plan`, `metallb-polarion-test-publish`, `metallb-manual-test-execution`, `metallb-e2e-automation`.

## User-provided inputs (agents must honor these)

Tasks are driven by data the user supplies (chat message, pasted URLs, or environment). Use this resolution order; **never invent** an Epic key or Google Doc URL.

| Input | Resolution order |
| ----- | ---------------- |
| **Jira Epic key** | Explicit value in the user message (e.g. `NET-1234`, `CNF-45678`) → optional `METALLB_JIRA_EPIC_KEY` in `.env` or `export` → if still missing, ask once before Phase 1/2 work. |
| **Google Doc URLs** | URLs pasted by the user (high-level vs detailed) → `POLARION_TRACE_HIGH_LEVEL_PLAN_URL` / `POLARION_TRACE_DETAILED_PLAN_URL` or `METALLB_HIGH_LEVEL_PLAN_URL` / `METALLB_DETAILED_PLAN_URL` in `.env` / shell → for Polarion traceability, `POLARION_TRACE_*` overrides `METALLB_*` when both are set. |
| **`KUBECONFIG`** | Path or `export KUBECONFIG=...` from the user → before any `oc`/`kubectl`, export it in the shell session → optional sanity check: `scripts/check_cluster_context.sh` or `scripts/check_cluster_context.sh /path/to/kubeconfig`. |

## Jira access (mandatory)

For Epic context, remote links, and linked issues:

1. **Always use** `adapters/jira_adapter.py` with `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_TOKEN` from `.env` (shell `export JIRA_*` overrides after load).
2. **Do not** use the Atlassian Cursor MCP/plugin for Jira unless the user **explicitly** asks for MCP or `.env` Jira credentials are missing after you report that once.
3. CLI check: `python3 adapters/jira_adapter.py --issue CNF-12345` (or `JiraAdapter.from_env().get_issue(...)` in scripts).

**Shell overrides:** For Polarion publish, `read_qe_env` loads `.env` then overlays `POLARION_*`, `METALLB_*`, `JIRA_*`, and `KUBECONFIG` from the process environment so one-off `export ...` values apply without editing files.

## Mandatory Output Path

### High-level test plan

- **Create / generate:** Return the **full validated test plan in the chat response** (markdown per skill template). **Do not** publish to Google Docs automatically.
- **Publish:** Only when the user **explicitly** asks to publish (or upload) the high-level plan to Google Docs—then use the publish pipeline below and return the Google Docs URL (unless they also asked for markdown in the same message).
- Do not persist test plan markdown files in the project workspace.

### Detailed test plan

- Final artifact is a formatted Google Doc (unless the user only asked for chat/local output).
- Return only the Google Docs URL unless the user explicitly asks for local files or pasted markdown.

## Mandatory Publish Pipeline

### High-level test plan (publish on explicit user request only)

1. Generate or reuse markdown from the approved draft in the conversation (in memory or a transient file under `.cursor/workspaces/agent-tmp/` — gitignored; never under tracked paths).
2. Validate: `python3 scripts/validate_test_plan.py <transient-path>` (the publish script also validates).
3. Publish only when the user asked to publish:
   - `scripts/validate_and_publish_test_plan.sh "High-Level Test Plan - <JIRA_KEY> - <Feature Name>"`
   - Provide markdown content via stdin.
4. Do not use `adapters/google_docs_adapter.py` or other ad-hoc Docs upload paths for final output.

### Detailed test plan (YAML + oc/kubectl)

1. Follow `.cursor/skills/metallb-detailed-test-plan/SKILL.md` and its `assets/template.md`.
2. Generate markdown in memory or under `.cursor/workspaces/agent-tmp/` only (gitignored; do not use `/tmp` or tracked repo paths).
3. Validate and publish using:
   - `scripts/validate_and_publish_detailed_test_plan.sh "Detailed Test Plan - <JIRA_KEY> - <Feature Name>"`
   - Provide markdown content via stdin.
4. Each test case must include copy-paste YAML fences and `oc`/`kubectl` commands per validated structure.

## Repository Analysis Location

- Clone/update analysis repos only under:
  - `.cursor/workspaces/metallb-repo-analysis/`
- **Clone URLs** (authoritative; also listed in `.cursor/skills/metallb-high-level-test-plan/SKILL.md` and **detailed** skill step 3):
  - `https://github.com/metallb/metallb-operator`
  - `https://github.com/metallb/metallb`
  - `https://github.com/metallb/frr-k8s`
- Local directory names after clone:
  - `metallb-operator`, `metallb`, `frr-k8s`
- **Detailed plans + cluster validation:** The agent must use these same trees when writing YAML/`oc` steps **and** when **`KUBECONFIG`** is used to run cases on a test cluster—refresh repos before cluster work and use source to debug failed steps (see `metallb-detailed-test-plan` skill and Phase 2 in `.cursor/skills/metallb-detailed-test-plan/references/metallb-qe-lifecycle.mdc`).

## Agent transient files (gitignored)

- Put **all** agent-generated transient artifacts (test-plan markdown for validation, scratch notes, intermediate exports) under **`.cursor/workspaces/agent-tmp/`** only.
- Do **not** write them to `/tmp`, the repo root, or other tracked paths. Override directory with `METALLB_AGENT_TMP_DIR` if needed.
- Publish scripts create temp files there via `scripts/lib/agent_tmp_dir.sh`.

### Detailed test plans (extra)

- Hardcode MetalLB namespace `metallb-system` in YAML and `oc`/`kubectl` commands unless the Epic explicitly names a different namespace (state that exception once under Prerequisites).
- Do not use ALL_CAPS substitution variables (`METALLB_NS`, `TEST_POOL_NAME`, etc.); use concrete object names and literal CIDRs, and derive per-node names in `bash` when needed (see `.cursor/skills/metallb-detailed-test-plan/SKILL.md`).
- Keep Google Docs output readable: no “reference only” YAML blocks, no prose crammed inside fenced YAML, and use plain (non-bold) labels for `Manifest (YAML):`, `Run:`, and `Expected:`; keep `**Purpose:**` for validator compatibility.
- In `## Placeholders`, use **grouped bullet lists** (Namespace / Baseline / test objects), not markdown tables—tables often paste as unusable plain text in Docs.

## Polarion testcase + LiveDoc (when the deliverable is Polarion)

When the user asks for **Polarion** test cases / LiveDoc modules (not only Google Docs):

1. Follow `.cursor/skills/metallb-polarion-test-publish/references/metallb-polarion-livedoc-workflow.mdc` and skill `.cursor/skills/metallb-polarion-test-publish/SKILL.md`.
2. **Mandatory:** after creating testcase work items and moving them into the module, call **`PolarionAdapter.publish_livedoc_home_page`** (or `build_livedoc_home_html` + `update_document_home_page`) so the **module home page HTML** includes full **Description**, **Setup**, **Step | Expected Result** tables, **Teardown**, and a **link to each testcase** under its title. **`build_livedoc_home_html` raises `ValueError`** if the output would include a "Linked Polarion test cases" section or `module-workitem` macros; do not ship a document that is only macro placeholders. If you PATCH custom HTML with `update_document_home_page`, run **`validate_livedoc_home_html_policy`** first unless you have an explicit, documented exception.
3. Reuse `adapters/polarion_livedoc.py`, `adapters/polarion_adapter.py`, and `adapters/polarion_test_publish.py`; publish via `scripts/publish_polarion_livedoc_tests.py --epic-module <import.path.to.epic>` (see `examples/polarion_livedoc_epic_module/sample_epic.py` as the template; customer-specific epic modules should live outside the shared tree or in a gitignored path).
