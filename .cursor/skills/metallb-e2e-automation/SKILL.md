---
name: metallb-e2e-automation
description: Add MetalLB upstream-style e2e tests under e2etest/ on the user's GitHub fork branch and validate via GitHub Actions; no PR unless user requests. Use in QE Phase 4.
---

# MetalLB e2e test automation (Phase 4)

## When to use

**Phase 4** of the MetalLB QE lifecycle: implement **automated** tests in the **product** repository’s `e2etest/` tree, validated on **KIND**-based flows in **GitHub CI** on the **user’s** GitHub account/fork.

**Prerequisite:** User **explicitly approved** completion of Phase 3 (first execution) for this feature set.

## Non-negotiables

- **Clone the user’s fork** (or repo the user specifies) using the **user’s** Git credentials; do not assume write access to `metallb/metallb` upstream unless the user has it.
- Create a **test branch**; commit new/updated tests under `e2etest/` (and supporting files if required by upstream patterns).
- **Push** to the user’s remote so **GitHub Actions** runs the existing workflows.
- **Do not open a pull request** by default. The deliverable is a **branch on the user’s clone/fork** with **CI green** (or documented failures). Open a PR only if the user explicitly asks.

## Repository facts (metallb/metallb)

- **Orchestration:** `tasks.py` exposes **invoke** tasks (run as `inv …`).
- **Local KIND dev cluster:** `inv dev-env` (see `dev-env/README.md`).
- **E2E:** `inv e2etest` with flags such as `--bgp-mode frr-k8s`, `--skip`, `--ginkgo-params` (see `e2etest/README.md`).

Example (adjust focus/skip for your tests):

```bash
inv dev-env
inv e2etest --skip "IPV6|DUALSTACK|FRR-MODE|L2" --bgp-mode frr-k8s --ginkgo-params "-v --focus 'ConfigurationState'"
```

Cleanup when done with local KIND: `inv dev-env-cleanup`.

## Workflow

1. **Confirm gate** — User approves automation phase; confirm **fork URL**, **branch name**, and target **repo** (`metallb` vs `metallb-operator` vs `frr-k8s`—most e2e live under **`metallb/metallb`**).

2. **Clone and branch** — `git clone` user fork, `git checkout -b <test-branch>`.

3. **Implement tests** — Follow existing `e2etest` packages, Ginkgo style, and dev-env assumptions documented in upstream `e2etest/README.md`.

4. **Local sanity (optional but recommended)** — If the user’s machine has Docker/KIND and invoke deps, run a **narrow** `inv e2etest` focus matching the new tests before relying solely on CI.

5. **Push and CI** — Push branch; monitor **Actions** on the **user’s** GitHub repo. Use `gh run watch` / UI as needed. Report workflow conclusion and link to the run.

6. **Response** — Summarize: branch name, commits, CI status, and any follow-ups (flakes, skipped suites).

## Analysis clone vs automation clone

- **Read-only code analysis** for plans remains under `.cursor/workspaces/metallb-repo-analysis/` per project rules.
- **Automation work** happens in the **user-provided clone path** (for example a separate directory); do not conflate the two unless the user wants a single workspace.

## Constraints

- No credentials in commits; use CI secrets patterns upstream already defines.
- Respect `.cursor/rules/metallb-qe-lifecycle.mdc` phase ordering.
