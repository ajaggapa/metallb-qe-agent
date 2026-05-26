# Progressive Skill Layout

This workspace uses a progressive skill structure inspired by agentskills.io:

- `SKILL.md`: primary behavior and execution guidance
- `assets/`: reusable templates and static skill assets
- `scripts/`: script entrypoints or command references used by the skill
- `references/`: policy/rule documents and lifecycle references used by the skill

Each MetalLB QE skill is self-contained with these directories so operational rules and execution helpers live alongside the skill that uses them.
