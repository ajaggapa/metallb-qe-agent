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

If neither Epic nor **approved** high-level plan context is available, ask for the Epic key and whether Phase 1 is **approved** before proceeding (see `.cursor/rules/metallb-qe-lifecycle.mdc`).

## QE Phase 2: cluster validation, bugs, Polarion timing

- **Gate:** Only run this skill after the user confirms **high-level plan approval**.
- **With `KUBECONFIG`:** Run **all** proposed test cases on the cluster; capture **observed** results and align **Expected:** lines with reality. Note per-step outcomes for early defect detection.
- **Triage:** If behavior is wrong, use Jira + code under `.cursor/workspaces/metallb-repo-analysis/` to decide **product bug** vs **procedure error**. **Bug:** file **Jira** with `project = OCPBUGS`, **component = `Networking / Metal LB`**, attach logs/evidence. **Procedure:** fix steps/YAML/commands and re-run on cluster before publishing/updating the Doc.
- **Polarion:** Publish testcase work items + LiveDoc under **OpenShift `CNF`** (default Polarion space **`CNF`**) **only after** the user **approves** the detailed Google Doc. Use `metallb-polarion-test-publish` and `metallb-polarion-livedoc-workflow` rules. Do not skip full home-page HTML embedding.
- **Next phase:** Do not run **Phase 3** (`metallb-manual-test-execution`) or **Phase 4** (`metallb-e2e-automation`) until the user explicitly approves moving on (and Polarion is done or explicitly deferred).

## Workflow

1. **Align with high-level coverage**
   - If a high-level plan exists, mirror its **same test case IDs and names** (`TC-01`, `TC-02`, …) and intents.
   - If not, derive cases from Jira acceptance criteria and code analysis (same quality bar as the high-level skill: happy path, negative/validation, reconciliation/state).

2. **Collect Jira and doc context**
   - Prefer Atlassian MCP tools (`searchAtlassian`, `getJiraIssue`, `getJiraIssueRemoteIssueLinks`, Confluence links from the Epic).
   - Fall back to `adapters/jira_adapter.py` only if MCP is unavailable.

3. **Refresh analysis repos** (same as high-level skill)
   - Under `.cursor/workspaces/metallb-repo-analysis/`:
     - `metallb-operator`, `metallb`, `frr-k8s`
   - Shallow clone or `git pull`; analyze `api/`, controllers, validation, and feature gates so YAML and commands match real CRDs and field names.

4. **Author executable steps**
   - For **each** test case, break **Procedure** into ordered steps (`#### Step 1`, `#### Step 2`, …).
   - Every step that applies or changes cluster state should include:
     - `Manifest (YAML):` (plain label, not bold) followed by a fenced `yaml` block the tester can save and apply.
     - `Run:` (plain label) followed by a fenced `bash` block using `oc` or `kubectl` (apply, get, describe, logs, wait, delete, debug).
   - Pure verification steps may omit YAML and use command-only blocks; still include an `Expected:` line (plain label, not bold).
   - Add **Cleanup** steps where resources must be removed to avoid cross-case interference.

5. **Namespace, literals, and Google Docs–friendly formatting (mandatory for detailed plans)**
   - **MetalLB namespace:** hardcode `metallb-system` in every manifest and command unless the Epic explicitly targets a different downstream layout (if so, state that once under Prerequisites and still avoid ALL_CAPS variables).
   - **No ALL_CAPS substitution variables** in YAML or shell (do not use `METALLB_NS`, `TEST_POOL_NAME`, `SPEAKER_STATE_NAME`, etc.). Use concrete object names (for example `cnf20333-baseline-pool`, `cnf20333-peer-bfd-missing`) and literal CIDRs (for example documentation range `192.0.2.0/24`). When the tester must target a speaker `ConfigurationState`, derive the node name from the cluster in `bash` (for example `NODE=$(oc get pod -n metallb-system -l app.kubernetes.io/component=speaker -o jsonpath='{.items[0].spec.nodeName}')` then `speaker-${NODE}`) instead of leaving a placeholder.
   - **Avoid noisy markdown that renders poorly in Google Docs:** do not prefix YAML with pseudo-headings or long bold lines such as “No apply — reference only.” Do not stuff explanatory prose inside fenced `yaml` blocks. Put instructions in normal sentences above the fence; keep fenced YAML strictly valid and copy-pasteable.
   - **Bold usage:** keep `**Purpose:**` (required by the validator). Use non-bold labels for `Manifest (YAML):`, `Run:`, and `Expected:` unless the high-level template demands otherwise.

6. **Placeholders section (required heading, literal-first content)**
   - Keep the heading `## Placeholders` (validator requirement).
   - Do **not** use a markdown pipe table: Google Docs import often turns it into a single unreadable text block. Use **short themed groups** instead: one-line intro, then `**Group title**` followed by `-` bullets (`backtick` values). Example groups: Namespace, Baseline pool, BGP/BFD test objects, Cleanup targets.

7. **Prerequisites**
   - **`## Prerequisites and Environment`**: cluster type, MetalLB/FRR operator install assumptions, required CRDs, feature gates.

8. **Render output with exact template**
   - Use `template.md` in this folder.
   - Keep generated content **in memory** or under `/tmp` only unless the user explicitly asks for a local file.

9. **Validate and publish**
   - Pipe markdown to:
     - `scripts/validate_and_publish_detailed_test_plan.sh "Detailed Test Plan - <JIRA_KEY> - <Feature Name>"`
   - Do not use `adapters/google_docs_adapter.py` for final publishing.
   - Fix validation errors and re-run before replying.

10. **Response to the user**
   - Return **only the Google Docs URL** unless the user explicitly asked for local files or pasted content.
   - Do **not** publish to **Polarion** in the same turn unless the user has **already** stated the detailed plan is **approved** for Polarion (see `.cursor/rules/metallb-qe-lifecycle.mdc`).

## Quality Constraints

- YAML must be syntactically valid and use CRD `apiVersion`/`kind`/`metadata` consistent with analyzed repos.
- Commands must be copy-pasteable; prefer `oc` for OpenShift with a one-line note that `kubectl` works where equivalent.
- Each test case must remain traceable to high-level **Purpose** / **Pass-Fail** intent.
- Never include credentials or values from `.env`.
- No persistent test-plan markdown under the project workspace (use stdin → `/tmp` → script).

## Output Contract

Match `template.md` sections:

- `# Detailed Test Plan: <Feature> (<JIRA_KEY>)`
- `## JIRA Reference` (ticket key + URL lines per validator)
- `## Related High-Level Test Plan` (link or “Generated from Epic …” if none)
- `## Prerequisites and Environment`
- `## Placeholders` (fixed literals table; see step 6 above)
- `## Detailed Test Cases` with `### TC-NN: …` and per-step YAML + `Run:` bash blocks
- `## References`

Minimum **three** detailed test cases (`TC-01` …), each with at least one `yaml` fence and one `bash`/`sh` fence containing `oc` or `kubectl`, per `scripts/validate_detailed_test_plan.py`.
