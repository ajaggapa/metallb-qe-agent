---
name: metallb-high-level-test-plan
description: Generate a high level test plan for MetalLB features using a Jira Epic key, linked design docs/PRs, and deep code analysis across metallb-operator, metallb, and frr-k8s. Use when the user asks for a high-level test plan, QA scope, or test cases for a MetalLB/OpenShift feature.
---

# MetalLB High-Level Test Plan

## Purpose

Create a consistent, evidence-based high-level test plan by combining:

- Jira Epic context (feature intent, links, acceptance notes)
- Design documents and PR references
- Source analysis of `metallb-operator`, `metallb`, and `frr-k8s`

## Required Inputs

- Jira Epic key (for example `NET-1234`)
- Optional explicit design doc links
- Optional constraints (environment, topology, protocol focus, release target)

**Resolution:** Prefer the Epic key and doc URLs **stated in the user message**. If the key is missing, check optional `METALLB_JIRA_EPIC_KEY` in `.env` (or shell `export`). If still missing, ask once before proceeding—do not guess keys.

**Google Doc title:** When the user asks to **publish**, use `scripts/validate_and_publish_test_plan.sh "High-Level Test Plan - <JIRA_KEY> - <Feature Name>"` with the **same** `<JIRA_KEY>` the user provided (normalize to uppercase if they gave a mixed-case key).

## QE Phase 1 and user gate

This skill covers **Phase 1** only. Phase 1 has **two agent steps** separated by user intent:

1. **Draft (default)** — User asks to *create* / *generate* a high-level test plan → return the full plan **in the chat response** (see **Output Contract**). **Do not** publish to Google Docs.
2. **Publish (explicit only)** — User asks to *publish* the high-level plan (to Google Docs) → run validation + `validate_and_publish_test_plan.sh` and return the Google Docs URL.

After publish, the user may edit the Doc and run **peer QE + Epic assignee (developer) review** until satisfied.

**Do not** start the **detailed** test plan (`metallb-detailed-test-plan`), Phase 3 execution, Polarion publish for procedures, or e2e automation **for the same Epic** until the user **explicitly states** the high-level plan is **approved** (with or without changes from the original agent draft).

## Workflow

1. **Collect Jira and doc context**
   - **Mandatory:** `adapters/jira_adapter.py` with `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_TOKEN` from `.env` (see `AGENTS.md` — Jira access). Use `JiraAdapter.from_env().get_issue(<key>)` and `get_remote_issue_links(<key>)` for Epic fields and PR/doc links.
   - **Do not** use the Atlassian Cursor MCP for Jira unless the user explicitly requests MCP or `.env` Jira credentials are unavailable (report once, then ask how to proceed).
   - Design docs: URLs from the Epic description, remote links, issue links, or URLs the user pasted in chat.

2. **Create temporary analysis workspace**
   - Clone into a project-local analysis folder (do not modify user repositories):
     - `.cursor/workspaces/metallb-repo-analysis/`
   - Use one subfolder per repository:
     - `.cursor/workspaces/metallb-repo-analysis/metallb-operator`
     - `.cursor/workspaces/metallb-repo-analysis/metallb`
     - `.cursor/workspaces/metallb-repo-analysis/frr-k8s`
   - If the folder already exists, refresh with `git fetch` / `git pull` (or reclone if corrupt).
   - Keep this folder out of normal source edits; it is analysis-only.
   - Repositories to clone:
     - `https://github.com/metallb/metallb-operator`
     - `https://github.com/metallb/metallb`
     - `https://github.com/metallb/frr-k8s`
   - Prefer shallow clone for speed.

3. **Analyze all three repos in parallel**
   - Prefer subagents (explore/general) per repo when allowed; otherwise analyze in a single session while covering all three repos:
     - `api/` CRD/type definitions
     - controllers/reconcilers
     - admission/validation paths
     - feature flags or configuration gates
   - Map logic ownership:
     - Operator-level orchestration in `metallb-operator`
     - Core feature logic and MetalLB CR handling in `metallb`
     - FRR integration CR handling in `frr-k8s`

4. **Define scope**
   - In Scope: directly impacted behavior and interfaces
   - Out of Scope / Limitations: explicitly untouched layers, unsupported permutations, known environmental dependencies
   - Webhook mode: determine whether the feature interacts with admission/validation webhooks and state explicitly whether both modes (enabled/disabled) are in scope (see **Webhook Mode Considerations** below)

5. **Write high-level test cases**
   - Include happy path, negative/validation path, and reconciliation/state propagation path.
   - For features touching CR validation, include both webhook-enabled and webhook-disabled variants (see **Webhook Mode Considerations**).
   - Prefer observable outcomes:
     - resource status/conditions
     - generated config/state objects
     - controller events/log patterns (when appropriate)
     - admission rejection messages (webhook-enabled) vs degraded status conditions (webhook-disabled)

6. **Render output with exact template**
   - Use the template in `assets/template.md`.
   - Keep the generated plan in-memory or under `.cursor/workspaces/agent-tmp/` only (gitignored; do not use `/tmp` or any tracked repo path unless the user explicitly asks for a committed file).

7. **Validate draft (before any response or publish)**
   - Run `python3 scripts/validate_test_plan.py <transient-markdown-path>` on the draft (e.g. `.cursor/workspaces/agent-tmp/high-level-test-plan-<JIRA_KEY>.md`).
   - If validation fails, fix and re-run before replying or publishing.

8. **Deliver draft in chat (default — do not publish)**
   - When the user asked to **create** / **generate** a high-level test plan, include the **full validated markdown** in the assistant message (all sections and test cases per **Output Contract**).
   - Briefly note that Google Docs publish happens only when they ask (e.g. “publish the high-level plan to Google Docs”).
   - **Do not** run `validate_and_publish_test_plan.sh` unless the user explicitly requests publish.

9. **Publish to Google Docs (only when user explicitly asks)**
   - Trigger phrases include: “publish”, “upload to Google Docs”, “put this in a Google Doc”, or equivalent for the **current** high-level plan.
   - Use the latest plan from the conversation (apply any edits the user requested since the draft).
   - Command path:
     - `scripts/validate_and_publish_test_plan.sh "High-Level Test Plan - <JIRA_KEY> - <Feature Name>"`
     - Feed markdown through stdin (validates again, then publishes).
   - Do not use `adapters/google_docs_adapter.py` for final test-plan publishing.
   - Return **only** the Google Docs URL unless the user also asked for the markdown in the same message.

## MetalLB deployment 

MetalLB is deployed in the cluster using metallb-operator located at https://github.com/metallb/metallb-operator
Deployment can be modified based on the metallb CRD spec section.
Test cases should consider the impact of various scenarios of a specific feature based on various possibilities of metallb deployment scenarios.
For example: metallb CR supports deployment with and without webhook. So there should be test cases that explore both the scenarios only if the feature behaves differently in both scenarios.


### How webhooks are controlled

| Deployment method | Mechanism to disable webhook |
| --- | --- |
| Helm chart (`metallb/metallb`) | `controller.webhookMode: disabled` in values; also `crds.validationFailurePolicy: Ignore` to let invalid CRs through |
| MetalLB Operator CR (`metallb.io/v1beta1 MetalLB`) | Operator passes `--webhook-mode` flag to the controller; check the operator version for a dedicated spec field (e.g. future `spec.controllerConfig` annotations or direct field) |
| Direct manifest | Remove or patch the `ValidatingWebhookConfiguration` resource, or set `failurePolicy: Ignore` |

### Mandatory test-plan guidance

1. **Scope statement:** Explicitly state whether the feature's test plan covers webhook-enabled only, webhook-disabled only, or both (preferred for validation-related features).
2. **Validation test cases:** For any test case exercising negative/invalid input:
   - Include a variant with the webhook **enabled** (expect admission rejection).
   - Include a variant with the webhook **disabled** (expect the controller to report an error condition on the resource status or via events, rather than crashing or silently ignoring the misconfiguration).
3. **Happy-path cases:** At minimum, verify the happy path works in both modes (feature functions correctly regardless of webhook presence).
4. **Transition scenarios (if relevant):** If the Epic touches webhook logic or deployment lifecycle, add a test case for toggling webhook mode at runtime (disable → verify controller-only validation → re-enable → verify admission enforcement resumes).
5. **Labeling:** Prefix or tag test cases that are webhook-mode-specific so reviewers can quickly identify them (e.g. `[Webhook: disabled]` in the test-case title or purpose).

### Code analysis pointers

When cloning repos in step 3 of the workflow, also inspect:

- `metallb/metallb` — `controller/main.go` or `cmd/` for `--webhook-mode` flag handling; `internal/webhooks/` or `api/` for admission logic.
- `metallb/metallb-operator` — `api/v1beta1/metallb_types.go` for CR spec fields; controller reconciliation to see how `webhookMode` propagates to the deployed controller args.
- Helm templates: `charts/metallb/templates/webhooks.yaml` for conditional rendering of `ValidatingWebhookConfiguration`.

## Quality Constraints

- Keep feature summary concise and concrete.
- Every test case must include purpose, procedure, expected result, and pass/fail criteria.
- Tie scope statements to evidence (Jira/doc/code paths).
- Never include credentials or secret values from `.env`.
- On **draft**: return the full plan in chat; do **not** publish to Google Docs.
- On **publish**: return the Google Docs URL (unless the user also asked for markdown).

## Output Contract

**Draft response (create / generate):** Include the complete plan markdown in the message using this structure:

Produce this structure:

- `# High-Level Test Plan: <Feature Name> (<JIRA_KEY>)`
- `## JIRA Reference`
- `## Feature Summary`
- `## Scope` with `### In Scope` and `### Out of Scope / Limitations`
- `## Test Cases` with at least 3 test cases (`TC-01` onward)
- `## References`

For references, include Jira link, design docs, and key PR/code links used in analysis.

## Follow-on: detailed manual plan

When the user needs **executable** steps (YAML manifests and `oc`/`kubectl` commands per test case), use the companion skill **`metallb-detailed-test-plan`** (`.cursor/skills/metallb-detailed-test-plan/SKILL.md`) and publish via `scripts/validate_and_publish_detailed_test_plan.sh`—**only after** the user confirms **Phase 1 approval** per `references/metallb-test-plan-workflow.mdc` and `.cursor/skills/metallb-detailed-test-plan/references/metallb-qe-lifecycle.mdc`.
