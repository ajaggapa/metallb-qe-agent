# metallb-qe-agent

Cursor-oriented workflows for MetalLB / OpenShift networking QE: high-level and detailed test plans (Google Docs), Polarion LiveDoc publishing, and a four-phase lifecycle with explicit approval gates.

See [AGENTS.md](AGENTS.md) for guardrails and [`.cursor/rules/metallb-qe-lifecycle.mdc`](.cursor/rules/metallb-qe-lifecycle.mdc) for phase definitions.

Local-only directories (repo analysis clones, tooling venvs) live under `.cursor/workspaces/` and are not committed. Copy `.env.example` to `.env` and fill in real values (`.env` stays gitignored).
