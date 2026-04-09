---
name: metallb-manual-test-execution
description: Run finalized manual/Polarion MetalLB test cases against an OpenShift cluster using KUBECONFIG and report results in a table. Use in QE Phase 3 after detailed plan and Polarion testcase IDs exist.
---

# MetalLB manual test execution (Phase 3)

## When to use

The user is in **Phase 3** of the MetalLB QE lifecycle: **test case first execution** on a cluster **using finalized procedures**, typically keyed by **Polarion testcase work item IDs**.

**Prerequisite:** User has **explicitly approved** proceeding past Phase 2 (detailed plan—and Polarion publish if required). Do not run this as a substitute for Phase 2 cluster validation unless the user directs.

## Required inputs

- **Polarion testcase IDs** (or ordered list the user confirms maps to procedures)—in execution order if relevant.
- **`KUBECONFIG`:** path or environment the user provides; never commit or paste secrets into repos or Docs.
- **Procedure source:** Polarion testcase steps and/or approved detailed Google Doc URL.

## Workflow

1. **Confirm gate** — Ask only if unclear: user should confirm Phase 2 approval and that this is the intended **first execution** cluster (prefer a **different** cluster from Phase 2 when the lifecycle calls for it).

2. **Configure CLI** — `export KUBECONFIG=...` (or use `--kubeconfig`), verify with `oc whoami` / `oc cluster-info` or equivalent.

3. **Per testcase**
   - Load **Setup**, **Steps**, **Expected results**, **Teardown** from Polarion (API/adapters if available) or from the user-pasted detailed plan.
   - Execute steps in order; capture relevant command output snippets, resource states, and log references for failures.
   - Run **Teardown** when specified so the next case is not polluted.

4. **Report** — Return a **markdown table** (or equivalent) with at least:

   | Polarion ID | Test title (short) | Result (Pass/Fail/Blocked/Skipped) | Notes |
   | ----------- | ------------------ | ------------------------------------ | ----- |

   For failures, include whether follow-up is **OCPBUGS** candidate vs **procedure/data** issue and next action.

5. **Bugs** — If a failure is triaged as a product bug, file **Jira** `project = OCPBUGS`, **component = `Networking / Metal LB`**, with logs and repro tied to the testcase ID.

## Constraints

- Do not store kubeconfig or tokens in the workspace or in Google Docs.
- Align with `.cursor/rules/metallb-qe-lifecycle.mdc` for phase gates.
