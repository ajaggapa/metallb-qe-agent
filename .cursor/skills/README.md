# Progressive Skill Layout

This workspace uses a progressive skill structure inspired by agentskills.io:

- `SKILL.md`: primary behavior and execution guidance
- `assets/`: reusable templates and static skill assets
- `scripts/`: script entrypoints or command references used by the skill
- `references/`: policy/rule documents and lifecycle references used by the skill

Each MetalLB QE skill is self-contained with these directories so operational rules and execution helpers live alongside the skill that uses them.

## Cross-skill conventions (all agents)

- **Detailed test plan steps** (`metallb-detailed-test-plan`): each `Expected:` block uses **`Run:`** + **`Sample output:`** with representative `oc`/`kubectl` terminal output — see `assets/template.md`.
- **Polarion publish** (`metallb-polarion-test-publish`): epic `steps` expected cells use **`expected_sample_output()`** with the same Run + Sample output shape; see `examples/polarion_livedoc_epic_module/sample_epic.py`.
- **Polarion delete** (`metallb-polarion-deletion-guardrails.mdc`): **two** user confirmations in chat; plan lists broken links; scripts delete only with dual `--confirm-token` / `--confirm-final`.
