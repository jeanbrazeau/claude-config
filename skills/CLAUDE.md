# skills/

Script-based agent workflows with shared orchestration framework.

## Files

| File        | What                                 | When to read                                  |
| ----------- | ------------------------------------ | --------------------------------------------- |
| `README.md` | Skills architecture, design, catalog | Understanding skills system design, migration |

## Subdirectories

| Directory             | What                                     | When to read                            |
| --------------------- | ---------------------------------------- | --------------------------------------- |
| `scripts/`            | Python package root for all skill code   | Executing skills, debugging behavior    |
| `planner/`            | Planning and execution workflows         | Creating implementation plans           |
| `refactor/`           | Refactoring analysis across dimensions   | Technical debt review, code quality     |
| `problem-analysis/`   | Structured problem decomposition         | Understanding complex issues            |
| `solution-design/`    | Perspective-parallel solution generation | Generating diverse solutions            |
| `decision-critic/`    | Decision stress-testing and critique     | Validating architectural choices        |
| `deepthink/`          | Structured reasoning for open questions  | Analytical questions without frameworks |
| `codebase-analysis/`  | Systematic codebase exploration          | Repository architecture review          |
| `prompt-engineer/`    | Prompt optimization and engineering      | Improving agent prompts                 |
| `incoherence/`        | Consistency detection                    | Finding spec/implementation mismatches  |
| `doc-sync/`           | Documentation synchronization            | Syncing docs across repos               |
| `leon-writing-style/` | Style-matched content generation         | Writing content matching user's style   |

## Script Invocation

All Python skill scripts are invoked as modules from `scripts/`:

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.<skill_name>.<module> --step 1 --total-steps N" />

Example:

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.problem_analysis.analyze --step 1 --total-steps 5" />

## Beads Integration

Skills optionally integrate with beads (bd) for persistent cross-session issue tracking:
- Planner: Creates feature/milestone issues, tracks progress during execution
- Refactor: (planned) Creates issues for technical debt findings
- Codebase Analysis: (planned) Creates issues for security/architecture findings

Integration is optional and gracefully falls back to TodoWrite when beads is unavailable.
See `.claude/conventions/beads-integration.md` for details.
