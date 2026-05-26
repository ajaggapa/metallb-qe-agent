# metallb-qe-agent

Cursor-oriented workflows for MetalLB / OpenShift networking QE: high-level test plans drafted in chat (Google Docs publish on request), detailed test plans (Google Docs), Polarion LiveDoc publishing, and a four-phase lifecycle with explicit approval gates.

See [AGENTS.md](AGENTS.md) for guardrails and [`.cursor/skills/metallb-detailed-test-plan/references/metallb-qe-lifecycle.mdc`](.cursor/skills/metallb-detailed-test-plan/references/metallb-qe-lifecycle.mdc) for phase definitions.

Local-only directories (repo analysis clones, tooling venvs, **agent temp output** at `.cursor/workspaces/agent-tmp/`) live under `.cursor/workspaces/` and are not committed. Agents must put transient markdown and similar artifacts only in that gitignored tree—not in `/tmp` or tracked paths. Copy `.env.example` to `.env` and fill in real values (`.env` stays gitignored).

**Jira:** Agents read Epic context through `adapters/jira_adapter.py` using `JIRA_*` in `.env` (see [AGENTS.md](AGENTS.md)); Atlassian MCP is not used for Jira unless you explicitly request it.
