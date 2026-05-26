---
name: metallb-detailed-test-plan
description: Expand MetalLB/OpenShift high-level test cases into a detailed manual test plan with copy-paste YAML manifests and oc/kubectl commands, grounded in Jira, design docs, and metallb-operator, metallb, and frr-k8s code. Use when the user asks for a detailed test plan, step-by-step test instructions, executable test cases, or YAML/commands for manual QA.
---

# MetalLB Detailed Test Plan

## Purpose

Turn each high-level test case into **operator-ready manual steps**: concrete Kubernetes/OpenShift YAML (as fenced blocks) and `oc` / `kubectl` commands the tester runs in order, with expected observations and cleanup where needed.

## Required Inputs

- **Jira Epic key** (for example `NET-1234`), and/or
- **Approved** high-level test plan: Google Doc URL (or export) that the user confirms is the **reviewed/approved** baseline—not a draft awaiting peer/developer sign-off
- Optional: **`KUBECONFIG`** (path or env) for a dedicated **test OpenShift** cluster
- Optional: target OpenShift/Kubernetes version, namespace conventions, or IP/pool constraints

**Resolution:** Epic key and Doc URL(s) come from the **user message first**; optional fallbacks are `METALLB_JIRA_EPIC_KEY` and pasted/linked Google URLs. For cluster work, **export `KUBECONFIG`** to the path the user gave (or they can `export` it themselves), then run `oc whoami` or `scripts/check_cluster_context.sh` before executing steps. If neither Epic nor **approved** high-level plan context is available, ask for the Epic key and whether Phase 1 is **approved** before proceeding (see `references/metallb-qe-lifecycle.mdc`).

**Publish title:** `scripts/validate_and_publish_detailed_test_plan.sh "Detailed Test Plan - <JIRA_KEY> - <Feature Name>"` must use the user’s Epic key in `<JIRA_KEY>`.

## QE Phase 2: cluster validation, bugs, Polarion timing

- **Gate:** Only run this skill after the user confirms **high-level plan approval**.
- **Product repos (mandatory context):** Detailed authoring **and** any validation on a real OpenShift cluster (`KUBECONFIG`) must use the **same three upstream repositories** as the high-level skill (clone URLs below). Refresh them before cluster work so reconciler logic, CRD schemas, admission rules, and status fields match what you infer from `oc` output. When a step **fails** on the cluster, debug by correlating symptoms with **source** in the right repo—for example operator wiring vs core MetalLB reconciliation vs frr-k8s BGP/FRR CR handling—not only logs on the cluster.
- **With `KUBECONFIG`:** Run **all** proposed test cases on the cluster; capture **observed** results and align **Expected:** lines with reality. Note per-step outcomes for early defect detection. **Before** executing steps, ensure `.cursor/workspaces/metallb-repo-analysis/` contains current checkouts of all three repos (see **Workflow** step 3).
- **Triage:** If behavior is wrong, use Jira + code under `.cursor/workspaces/metallb-repo-analysis/` (search controllers, webhooks, `api/` types, and feature gates across **metallb-operator**, **metallb**, and **frr-k8s**) to decide **product bug** vs **procedure error**. Cite concrete file or package paths when explaining root cause. **Bug:** file **Jira** with `project = OCPBUGS`, **component = `Networking / Metal LB`**, attach logs/evidence. **Procedure:** fix steps/YAML/commands and re-run on cluster before publishing/updating the Doc.
- **Polarion:** Publish testcase work items + LiveDoc under **OpenShift `CNF`** (default Polarion space **`CNF`**) **only after** the user **approves** the detailed Google Doc. Use `metallb-polarion-test-publish` and `.cursor/skills/metallb-polarion-test-publish/references/metallb-polarion-livedoc-workflow.mdc`. Do not skip full home-page HTML embedding.
- **Next phase:** Do not run **Phase 3** (`metallb-manual-test-execution`) or **Phase 4** (`metallb-e2e-automation`) until the user explicitly approves moving on (and Polarion is done or explicitly deferred).

## Workflow

1. **Align with high-level coverage**
   - If a high-level plan exists, mirror its **same test case IDs and names** (`TC-01`, `TC-02`, …) and intents.
   - If not, derive cases from Jira acceptance criteria and code analysis (same quality bar as the high-level skill: happy path, negative/validation, reconciliation/state).

2. **Collect Jira and doc context**
   - **Mandatory:** `adapters/jira_adapter.py` with `.env` `JIRA_*` credentials (`JiraAdapter.from_env()` — same policy as `metallb-high-level-test-plan` and `AGENTS.md`). Do not use Atlassian MCP for Jira unless the user explicitly requests it or credentials are missing.

3. **Refresh analysis repos** (same URLs and layout as `metallb-high-level-test-plan`)
   - Parent directory: `.cursor/workspaces/metallb-repo-analysis/`
   - **Repositories to clone or update** (shallow clone or `git pull`):
     - `https://github.com/metallb/metallb-operator`
     - `https://github.com/metallb/metallb`
     - `https://github.com/metallb/frr-k8s`
   - Local folder names after clone: `metallb-operator`, `metallb`, `frr-k8s` (same as the high-level skill).
   - **For authoring:** Inspect `api/`, controllers/reconcilers, admission/validation, and feature gates so YAML and `oc` commands match real CRDs and field names.
   - **For cluster validation failures:** Use these trees as the **product truth**—trace conditions, `ConfigurationState`, BGP errors, or webhook denials back to reconciler code and CRD validation in the appropriate repo (operator orchestration vs `metallb` core vs `frr-k8s` integration).

4. **Author executable steps**
   - For **each** test case, break **Procedure** into ordered steps (`#### Step 1`, `#### Step 2`, …).
   - Every step that applies or changes cluster state should include:
     - `Manifest (YAML):` (plain label, not bold) followed by a fenced `yaml` block the tester can save and apply.
     - `Run:` (plain label) followed by a fenced `bash` block using `oc` or `kubectl` (apply, get, describe, logs, wait, delete, debug).
   - Pure verification steps may omit YAML and use command-only blocks; still include an `Expected:` line (plain label, not bold).
   - Add **Cleanup** steps where resources must be removed to avoid cross-case interference.

5. **Namespace, literals, and Google Docs–friendly formatting (mandatory for detailed plans)**
   - **MetalLB namespace:** hardcode `metallb-system` in every manifest and command unless the Epic explicitly targets a different downstream layout (if so, state that once under Prerequisites and still avoid ALL_CAPS variables).
   - **No ALL_CAPS substitution variables** in YAML or shell (do not use `METALLB_NS`, `TEST_POOL_NAME`, `SPEAKER_STATE_NAME`, etc.). Use concrete object names (for example `example-baseline-pool`, `example-bgp-peer-fault`) and literal CIDRs (for example documentation range `192.0.2.0/24`). When the tester must target a speaker `ConfigurationState`, derive the node name from the cluster in `bash` (for example `NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker -o jsonpath='{.items[0].spec.nodeName}')` then `speaker-${NODE}`) instead of leaving a placeholder.
   - **Avoid noisy markdown that renders poorly in Google Docs:** do not prefix YAML with pseudo-headings or long bold lines such as “No apply — reference only.” Do not stuff explanatory prose inside fenced `yaml` blocks. Put instructions in normal sentences above the fence; keep fenced YAML strictly valid and copy-pasteable.
   - **Bold usage:** keep `**Purpose:**` (required by the validator). Use non-bold labels for `Manifest (YAML):`, `Run:`, and `Expected:` unless the high-level template demands otherwise.

6. **Placeholders section (required heading, literal-first content)**
   - Keep the heading `## Placeholders` (validator requirement).
   - Do **not** use a markdown pipe table: Google Docs import often turns it into a single unreadable text block. Use **short themed groups** instead: one-line intro, then `**Group title**` followed by `-` bullets (`backtick` values). Example groups: Namespace, Baseline pool, BGP/BFD test objects, Cleanup targets.

7. **Prerequisites**
   - **`## Prerequisites and Environment`**: cluster type, MetalLB/FRR operator install assumptions, required CRDs, feature gates.

8. **Render output with exact template**
   - Use `assets/template.md` in this folder.
   - Keep generated content **in memory** or under `.cursor/workspaces/agent-tmp/` only (gitignored) unless the user explicitly asks for a tracked local file.

9. **Validate and publish**
   - Pipe markdown to:
     - `scripts/validate_and_publish_detailed_test_plan.sh "Detailed Test Plan - <JIRA_KEY> - <Feature Name>"`
   - Do not use `adapters/google_docs_adapter.py` for final publishing.
   - Fix validation errors and re-run before replying.

10. **Response to the user**
   - Return **only the Google Docs URL** unless the user explicitly asked for local files or pasted content.
   - Do **not** publish to **Polarion** in the same turn unless the user has **already** stated the detailed plan is **approved** for Polarion (see `references/metallb-qe-lifecycle.mdc`).

## Quality Constraints

- YAML must be syntactically valid and use CRD `apiVersion`/`kind`/`metadata` consistent with analyzed repos.
- Commands must be copy-pasteable; prefer `oc` for OpenShift with a one-line note that `kubectl` works where equivalent.
- Each test case must remain traceable to high-level **Purpose** / **Pass-Fail** intent.
- Never include credentials or values from `.env`.
- No persistent test-plan markdown under tracked repo paths (use stdin → `.cursor/workspaces/agent-tmp/` → publish script).

## Output Contract

Match `assets/template.md` sections:

- `# Detailed Test Plan: <Feature> (<JIRA_KEY>)`
- `## JIRA Reference` (ticket key + URL lines per validator)
- `## Related High-Level Test Plan` (link or “Generated from Epic …” if none)
- `## Prerequisites and Environment`
- `## Placeholders` (fixed literals table; see step 6 above)
- `## Detailed Test Cases` with `### TC-NN: …` and per-step YAML + `Run:` bash blocks
- `## References`

Minimum **three** detailed test cases (`TC-01` …), each with at least one `yaml` fence and one `bash`/`sh` fence containing `oc` or `kubectl`, per `scripts/validate_detailed_test_plan.py`.
