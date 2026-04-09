---
name: metallb-high-level-test-plan
description: Generate a high-level test plan for MetalLB features using a Jira Epic key, linked design docs/PRs, and deep code analysis across metallb-operator, metallb, and frr-k8s. Use when the user asks for a high-level test plan, QA scope, or test cases for a MetalLB/OpenShift feature.
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

If required inputs are missing, ask for the Epic key before proceeding.

## QE Phase 1 and user gate

This skill covers **Phase 1** only. After publishing the Google Doc, **stop** and let the user run **peer QE + Epic assignee (developer) review**, edit the Doc, and iterate until satisfied.

**Do not** start the **detailed** test plan (`metallb-detailed-test-plan`), Phase 3 execution, Polarion publish for procedures, or e2e automation **for the same Epic** until the user **explicitly states** the high-level plan is **approved** (with or without changes from the initial generation).

## Workflow

1. **Collect Jira and doc context**
   - Prefer Atlassian MCP tools:
     - `searchAtlassian` to locate the Epic and related docs
     - `getJiraIssue` for issue details
     - `getJiraIssueRemoteIssueLinks` for PR/doc links
   - If MCP is unavailable, fall back to local adapter workflow via `adapters/jira_adapter.py`.

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

5. **Write high-level test cases**
   - Include happy path, negative/validation path, and reconciliation/state propagation path.
   - Prefer observable outcomes:
     - resource status/conditions
     - generated config/state objects
     - controller events/log patterns (when appropriate)

6. **Render output with exact template**
   - Use the template in `template.md`.
   - Keep the generated plan in-memory (do not save a persistent local output file unless the user explicitly asks).

7. **Run validation hook**
   - Validate via transient content only (no project-local markdown artifacts).
   - Preferred command path is the combined pipeline in Step 8.
   - If validation fails, fix and re-run before final response.

8. **Upload to Google Docs**
   - Mandatory command path:
     - `scripts/validate_and_publish_test_plan.sh "High-Level Test Plan - <JIRA_KEY> - <Feature Name>"`
     - Feed markdown plan content through stdin.
   - This command validates content and publishes using the project-managed runtime.
   - Do not use `adapters/google_docs_adapter.py` for final test-plan publishing.
   - This is mandatory to ensure consistent formatting (title styles, section headings, bold inline labels, list rendering, clickable URL links in references).
   - Use title format: `High-Level Test Plan - <JIRA_KEY> - <Feature Name>`.
   - Include the Google Docs link in the final response.

## Quality Constraints

- Keep feature summary concise and concrete.
- Every test case must include purpose, procedure, expected result, and pass/fail criteria.
- Tie scope statements to evidence (Jira/doc/code paths).
- Never include credentials or secret values from `.env`.
- Always return the generated Google Docs URL.

## Output Contract

Produce this structure:

- `# High-Level Test Plan: <Feature Name> (<JIRA_KEY>)`
- `## JIRA Reference`
- `## Feature Summary`
- `## Scope` with `### In Scope` and `### Out of Scope / Limitations`
- `## Test Cases` with at least 3 test cases (`TC-01` onward)
- `## References`

For references, include Jira link, design docs, and key PR/code links used in analysis.

## Follow-on: detailed manual plan

When the user needs **executable** steps (YAML manifests and `oc`/`kubectl` commands per test case), use the companion skill **`metallb-detailed-test-plan`** (`.cursor/skills/metallb-detailed-test-plan/SKILL.md`) and publish via `scripts/validate_and_publish_detailed_test_plan.sh`—**only after** the user confirms **Phase 1 approval** per `.cursor/rules/metallb-qe-lifecycle.mdc`.
