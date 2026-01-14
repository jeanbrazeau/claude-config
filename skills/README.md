# Skills System

## Overview

Script-based agent workflows with shared orchestration framework. Skills implement multi-step workflows (planning, refactoring, analysis) through Python scripts that output structured XML commands. Each skill is invoked via script, not free-form agent exploration.

## Architecture

```
skills/
  __init__.py              # Package marker
  _bootstrap.py            # sys.path setup pattern documentation

  lib/                     # Shared framework (550+ lines extracted)
    workflow/              # Orchestration primitives
      types.py             # AgentRole, Routing, Dispatch, Step, QRState
      formatters/          # XML and text output
        xml.py             # 26 XML formatters for structured output
        text.py            # Plain text formatters for simple skills
      cli.py               # Argument parsing utilities

  planner/                 # Planning and execution workflows
    scripts/
      planner.py           # 13-step planning workflow
      executor.py          # 9-step execution workflow
      qr/*.py              # Quality review sub-workflows
      tw/*.py              # Technical writer sub-workflows
      dev/*.py             # Developer sub-workflows
      shared/              # Compatibility layer (temporary)
    resources/             # Authoritative specifications

  refactor/                # Refactoring analysis
  problem-analysis/        # Problem decomposition
  decision-critic/         # Decision stress-testing
  deepthink/               # Structured reasoning for open questions
  codebase-analysis/       # Repository exploration
  prompt-engineer/         # Prompt optimization
  incoherence/             # Consistency detection
  doc-sync/                # Documentation synchronization
  leon-writing-style/      # Style-matched content generation
```

## Beads Integration

Skills optionally integrate with [beads](https://github.com/solatis/beads) (`bd`) for persistent cross-session issue tracking. Integration is graceful - skills function normally when beads is unavailable.

### Type-Safe API

The `skills.lib.beads` module provides a type-safe wrapper around `bd` CLI commands:

```python
from skills.lib.beads import (
    IssueType, IssueStatus, DependencyType,  # Enums for type safety
    IssueId, IssueData,                      # Value objects
    is_beads_available, create_issue,        # API functions
)

# Type-safe issue creation
if is_beads_available():
    issue_id = create_issue(
        title="Implement authentication",
        issue_type=IssueType.FEATURE,        # Enum prevents typos
        priority=1,
        labels=["security", "backend"],
        deps=["AUTH-001"],                   # Accepts strings or IssueId objects
    )
    # Returns: IssueId(id="AUTH-002") or None

    # Type-safe status updates
    update_status(issue_id, IssueStatus.IN_PROGRESS)  # Enum provides autocomplete

    # Structured query results
    ready_issues = get_ready_issues(priority=1)
    # Returns: list[IssueData] with typed fields (id, title, priority, type, status)
```

**Benefits over raw strings:**
- Compile-time validation: Invalid enum values caught by type checker
- IDE autocomplete: Enums list all valid values
- Runtime validation: IssueId verifies format (e.g., "PRJ-123")
- Structured returns: IssueData replaces dict with typed fields
- Backward compatible: Functions accept both enums and strings

**Available types:**
- `IssueType`: BUG, FEATURE, TASK, EPIC, CHORE
- `IssueStatus`: OPEN, IN_PROGRESS, BLOCKED, CLOSED
- `DependencyType`: BLOCKS, RELATED, PARENT_CHILD, DISCOVERED_FROM
- `IssueId`: Value object with format validation (matches `[A-Z]+-\d+`)
- `IssueData`: Structured issue information (replaces `list[dict]`)

### Integration Points

**Planner skill** creates and tracks issues across planning and execution phases:

1. **Planning (planner.py step 5)**: After writing plan, optionally create:
   - Feature issue (epic) for the overall goal
   - Milestone issues (tasks) for each implementation wave
   - Dependency links between milestones

2. **Execution (executor.py steps 1, 3, 9)**:
   - **Step 1 (Wave Planning)**: Search for existing issues, note milestone IDs
   - **Step 3 (Implementation)**: Update milestone status as work progresses
   - **Step 9 (Retrospective)**: Close completed milestones and parent feature

**Feature flag pattern:**
```python
# In STEPS configuration
STEPS = {
    1: {
        "title": "Wave Planning",
        "beads_tracking": True,  # Enable beads guidance for this step
    },
}

# In step formatter
if info.get("beads_tracking") and is_beads_available():
    actions.extend([
        "OPTIONAL BEADS TRACKING:",
        "  bd update [MILESTONE-ID] --status in_progress",
        "  bd close [MILESTONE-ID] \"Completed\"",
    ])
```

**Flags:**
- `beads_tracking`: Enable issue tracking guidance (planner step 5, executor steps 1, 3)
- `beads_close`: Enable close guidance in retrospective (executor step 9)

**Graceful degradation:** All beads calls check `is_beads_available()` first. When beads unavailable:
- `create_issue()` returns None (caller handles gracefully)
- `update_status()`, `close_issue()` return False (no-op)
- `get_ready_issues()` returns empty list
- Skills continue normally using TodoWrite for in-session tracking

### Usage Examples

**Creating issues in planner:**
```python
from skills.lib.beads import IssueType, create_issue

# Create parent feature issue
feature_id = create_issue(
    title="Implement user authentication system",
    issue_type=IssueType.FEATURE,
    description="OAuth2 + JWT tokens + role-based access",
    priority=1,
)

# Create milestone issues with dependencies
milestone_ids = []
for i, milestone in enumerate(plan.milestones):
    mid = create_issue(
        title=f"Milestone {i+1}: {milestone.title}",
        issue_type=IssueType.TASK,
        priority=2,
        deps=[str(feature_id)] if feature_id else [],  # Link to parent
    )
    milestone_ids.append(mid)
```

**Tracking progress in executor:**
```python
from skills.lib.beads import IssueStatus, update_status, close_issue

# Starting a milestone
update_status("AUTH-002", IssueStatus.IN_PROGRESS)

# After completion
close_issue("AUTH-002", reason="All code implemented and tests passing")
```

**Querying ready work:**
```python
from skills.lib.beads import get_ready_issues

# Get high-priority issues with no blockers
ready = get_ready_issues(priority=1)
for issue in ready:
    # issue is IssueData with typed fields
    print(f"{issue.id}: {issue.title} [{issue.priority}]")
```

### Why Beads Integration

**Cross-session continuity:** Skills like planner create work that spans multiple sessions. Beads persists:
- Feature scope and milestones across conversation compaction
- Blocked/ready status for resuming work
- Dependency chains for complex features

**Without beads:** TodoWrite tracks in-session work but doesn't persist across sessions. After compaction, agent loses context about multi-session features.

**With beads:** Issues survive compaction. Agent can resume by querying `bd ready` to find unblocked work, review issue descriptions for context, and continue from previous session's stopping point.

**Optional by design:** Not all skills need persistence. Analysis skills (refactor, codebase-analysis) produce output consumed immediately. Only planner creates multi-session tracking issues.

## Data Flow

```
User request
  |
  v
Skill activation (.skill descriptor)
  |
  v
Script invocation (python3 scripts/*.py --step N --total-steps M)
  |
  v
Workflow orchestration (lib/workflow)
  |
  +-> Step logic (read context, compute actions)
  +-> Format output (XML with <DO>, <NEXT>, routing)
  +-> Print to stdout
  |
  v
Agent reads XML output
  |
  +-> Executes <DO> actions
  +-> Routes via <NEXT> (linear/branch/terminal)
  |
  v
Next step invocation (python3 scripts/*.py --step N+1 ...)
```

Quality Review (QR) loops use three-pillar pattern:

```
Work Step (--qr-fail=false)
  |
  v
Format XML with actions, routing
  |
  v
QR Step (review work)
  |
  v
Gate Step (--qr-status=pass|fail)
  |
  +-- PASS --> Next step or COMPLETE
  |
  +-- FAIL --> Work Step (--qr-fail=true, --qr-iteration=N+1)
```

## Why This Structure

**Script-based activation over free-form**: Free-form workflows drift. Agent explores first, skips steps, invents better approaches. Scripts enforce consistent behavior through structured XML output. Skills activate via `.skill` descriptor; agent invokes script immediately.

**lib/workflow/ shared framework**: Extracted 550+ lines of duplication from planner, refactor, problem-analysis, decision-critic. Framework provides types (AgentRole, Routing, Dispatch, Step, QRState), formatters (26 XML + text), and CLI utilities. New skills compose existing primitives instead of reimplementing orchestration.

**Compatibility layer during migration**: planner/scripts/shared/ temporarily re-exports lib/workflow to preserve existing imports. All planner mode scripts now import lib/workflow directly. Compatibility layer removed after remaining skills migrate.

**Bootstrap pattern over PYTHONPATH**: Skills use inline sys.path setup to add .claude/ for `from skills.*` imports. No external environment configuration. Pattern simplified from old 6-line repetitive `.parent.parent...` to 4-line `.parents[N]` approach documented in \_bootstrap.py.

**scripts/ subdirectory convention**: All skills place workflow scripts in `scripts/` subdirectory. Complex skills (planner) organize by agent role (qr/, tw/, dev/). Simple skills (problem-analysis) have single script. Convention makes skills discoverable.

**SKILL.md activation metadata**: Each skill has SKILL.md with YAML frontmatter (name, description) for skill system. Description includes trigger conditions and immediate-invoke instruction. Agent reads SKILL.md to understand when and how to activate skill.

**Resources as authoritative sources**: planner/resources/ contains planner-specific templates (plan-format.md, explore-output-format.md). Universal conventions live in .claude/conventions/ (structural.md, temporal.md, severity.md, intent-markers.md, documentation.md, diff-format.md). Scripts inject conventions at runtime via get_convention(). No manual sync for most resources. Resources embedded in agent prompts require manual sync.

## Design Decisions

**AgentRole enum over string literals**: String literals ("develper") allow typos. Enum provides compile-time validation, IDE autocomplete, exhaustive pattern matching. Matches actual agent system (quality-reviewer, technical-writer, developer).

**Routing union type (Linear | Branch | Terminal)**: Makes invalid states unrepresentable. Can't have both if_pass and terminal. Pattern matching on routing type is explicit. Matches actual usage (mutually exclusive routing modes).

**Stateless formatters over template classes**: All formatters are pure functions (input -> XML string). No object state. Deterministic output. Easy to test. Composable - actions list mixes XML blocks and plain strings.

**Two-layer composition**: Guidance layer (get_step_guidance() returns dict with title/actions/next) + rendering layer (format_step_output() assembles XML). Actions list contains plain strings and XML blocks. All formatters return strings so mixing works seamlessly.

**QRState three-pillar pattern**: iteration (loop count), failed (entry state flag), status (prior result). Both failed and status needed: failed indicates entering step to fix issues, status is QR result from previous step. All QR workflows use consistent CLI flags (--qr-iteration, --qr-fail, --qr-status).

**Skill-specific types NOT in framework**: planner-specific types (FlatCommand, BranchCommand, NextCommand, GuidanceResult) live in planner/scripts/shared/domain.py. These are guidance layer types, not framework primitives. xml.py imports them via importlib to avoid circular dependency.

**Depth-based .parents[N] calculation**: Bootstrap pattern uses .parents[N] where N depends on script depth relative to .claude/ root. scripts/_.py uses .parents[3], scripts/_/\*.py uses .parents[4]. Documented in \_bootstrap.py for reference.

## Invisible Knowledge

Constraints discovered through debugging that aren't obvious from code structure:

1. **No system reminder injection**: Claude Code cannot inject system reminders or messages after sub-agent returns. Solution B patterns (inject reminder after Task tool returns) are categorically non-feasible. All guidance must come from script output or sub-agent output itself.

2. **Turn boundary isolation**: Guidance in prior turn (script output) is not re-read after sub-agent returns. Agent acts on fresh sub-agent output without referencing earlier instructions. Example: `<post_qr_routing>` block in step 6 output is forgotten after QR sub-agent returns with findings.

3. **Sub-agent output is the intervention point**: To influence orchestrator behavior after sub-agent returns, the sub-agent's own output must include the guidance. This is why `format_qr_file_output()` includes an `<orchestrator_action>` block reminding the orchestrator to invoke the gate step before fixing.

## Invariants

1. **Script activation required**: Skills MUST activate via script invocation. Agent does NOT explore before invoking. Script IS the workflow.

2. **Structured XML output**: Workflow scripts output XML with <DO> (actions), <NEXT> (continuation command), <INVOKE_AFTER> (routing). Agent reads XML and executes as specified.

3. **Step immutability**: Once script outputs XML for step N, agent executes exactly that step. No interpretation. No improvement. Follow output.

4. **QR loop completeness**: Every QR checkpoint has three pillars: STATE BANNER (format_qr_banner), STOP CONDITION (format_gate_step), RE-VERIFY MODE (--qr-iteration + flags). Missing any pillar allows agent to skip verification.

5. **Bootstrap pattern uniformity**: All scripts use identical 4-line sys.path setup. Only difference is .parents[N] value based on depth. Pattern documented in \_bootstrap.py.

6. **Import compatibility during migration**: During migration, `from shared import format_step_output` works identically to `from skills.lib.workflow.formatters import format_step_output`. Compatibility layer removed after migration complete.

## Tradeoffs

1. **Script rigidity vs flexibility**: Scripts enforce consistency but reduce adaptability. Agent cannot adjust workflow mid-execution. Accepted because consistency prevents drift and ensures quality gates run.

2. **XML verbosity vs precision**: XML output is verbose compared to natural language. Accepted because structured output eliminates ambiguity. Agent executes exactly what script specifies.

3. **Duplication during migration**: Compatibility layer (planner/scripts/shared/) duplicates lib/workflow exports temporarily. Removed after all skills migrate. Migration burden worth long-term reduction in duplication.

4. **More files vs single script**: lib/workflow has 7+ files vs monolithic script. Accepted because separation (types, formatters/xml, formatters/text, cli) prevents 700+ line file and enables selective imports.

5. **Learning curve for new skills**: New skills must learn lib/workflow API (types, formatters, CLI utilities). Offset by reduced boilerplate - no need to reimplement orchestration, XML formatting, QR loop logic.

## Skills Catalog

| Skill              | Steps    | Purpose                                 | Quality Gates |
| ------------------ | -------- | --------------------------------------- | ------------- |
| planner            | 13 + 9   | Plan creation + execution               | 3 QR loops    |
| refactor           | 7        | Refactoring analysis across dimensions  | None          |
| problem-analysis   | 4        | Structured problem decomposition        | None          |
| decision-critic    | Variable | Decision stress-testing                 | None          |
| deepthink          | 14       | Structured reasoning for open questions | None          |
| codebase-analysis  | 4        | Systematic repository exploration       | None          |
| prompt-engineer    | Variable | Prompt optimization                     | None          |
| incoherence        | Variable | Consistency detection                   | None          |
| doc-sync           | Variable | Cross-repo documentation sync           | None          |
| leon-writing-style | Variable | Style-matched content generation        | None          |

**Quality gates**: Only planner uses QR loops. Other skills are analysis/synthesis workflows without iterative refinement.

## Bootstrap Pattern

All workflow scripts use this pattern to enable `from skills.*` imports:

```python
import sys
from pathlib import Path

# Add .claude/ to path for skills.* imports
_claude_dir = Path(__file__).resolve().parents[N]  # N depends on depth
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

from skills.lib.workflow.formatters import format_step_output
from skills.lib.workflow.types import Step, LinearRouting
```

**Depth guide**:

- `skills/*/scripts/*.py`: `.parents[3]` (script -> scripts -> skill -> skills -> .claude)
- `skills/*/scripts/*/*.py`: `.parents[4]` (script -> subdir -> scripts -> skill -> skills -> .claude)

**Why this pattern**:

- No PYTHONPATH dependency - works in any invocation context
- Simplified from old 6-line pattern using repetitive `.parent.parent...`
- Adds .claude/ only once (idempotent check)
- Absolute path resolution prevents relative path issues

**Migration from old pattern**:

Before (6 lines, repetitive):

```python
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent  # Repetitive
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

After (4 lines, .parents[N]):

```python
import sys
from pathlib import Path

_claude_dir = Path(__file__).resolve().parents[3]
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))
```

## Usage Examples

### Creating a new simple skill

```python
import sys
from pathlib import Path

# Add .claude/ to path for skills.* imports
_claude_dir = Path(__file__).resolve().parents[3]
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

from skills.lib.workflow.formatters.text import format_text_output

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step == 1:
        print(format_text_output(
            step=1,
            total=args.total_steps,
            title="Analyze Problem",
            actions=["Read codebase", "Identify issues"],
            brief="Initial analysis",
            next_title="Propose Solution",
        ))
    elif args.step == 2:
        print(format_text_output(
            step=2,
            total=args.total_steps,
            title="Propose Solution",
            actions=["Design fix", "Document approach"],
            brief="Solution design",
            next_title=None,  # Terminal step
        ))

if __name__ == "__main__":
    main()
```

### Creating a skill with QR loops

```python
import sys
from pathlib import Path

# Add .claude/ to path for skills.* imports
_claude_dir = Path(__file__).resolve().parents[3]
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

from skills.lib.workflow.formatters import format_step_output, format_gate_step
from skills.lib.workflow.types import (
    Step, QRState, GateConfig, AgentRole,
    LinearRouting, BranchRouting
)

STEPS = {
    1: Step(
        title="Implementation",
        actions=["Write code", "Run tests"],
        routing=LinearRouting(),
    ),
    2: Step(
        title="QR: Review Implementation",
        actions=["Check code quality", "Verify tests"],
        routing=BranchRouting(if_pass=4, if_fail=3),
    ),
    # Step 3 is gate (no entry in STEPS dict)
}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", action="store_true")
    parser.add_argument("--qr-status", type=str, choices=["pass", "fail"])
    args = parser.parse_args()

    qr = QRState(
        iteration=args.qr_iteration,
        failed=args.qr_fail,
        status=args.qr_status,
    )

    if args.step == 3:  # Gate step
        gate = GateConfig(
            qr_name="Implementation Review",
            work_step=1,
            pass_step=4,
            pass_message="Implementation verified",
            self_fix=True,
            fix_target=AgentRole.DEVELOPER,
        )
        print(format_gate_step(
            script="script",
            step=3,
            total=args.total_steps,
            title="Gate: Route Based on QR",
            qr=qr,
            gate=gate,
        ))
    else:
        # Regular step
        step_config = STEPS[args.step]
        # ... format_step_output ...

if __name__ == "__main__":
    main()
```

### Migrating from planner/scripts/shared to lib/workflow

Before (imports from shared/):

```python
from shared import (
    QRState,
    GateConfig,
    format_step_output,
    format_gate_step,
)
```

After (direct lib.workflow imports):

```python
import sys
from pathlib import Path

# Add .claude/ to path for skills.* imports
_claude_dir = Path(__file__).resolve().parents[3]
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

from skills.lib.workflow.types import QRState, GateConfig
from skills.lib.workflow.formatters import format_step_output, format_gate_step
```

## Common Patterns

### Composing XML blocks in actions

```python
from skills.lib.workflow.formatters import (
    format_state_banner,
    format_forbidden,
    format_expected_output,
)

actions = [
    format_state_banner("checkpoint_name", iteration=2, mode="re-verify"),
    "",
    "TASK: Fix identified issues",
    "",
    format_forbidden([
        "Do not modify unrelated files",
        "Do not change API contracts",
    ]),
    "",
    format_expected_output([
        "All QR issues resolved",
        "Tests passing",
    ]),
]
```

### Sub-agent dispatch

```python
from skills.lib.workflow.formatters import format_subagent_dispatch
from skills.lib.workflow.types import AgentRole

actions = [
    "Parallel exploration across dimensions:",
    "",
    format_subagent_dispatch(
        agent=AgentRole.EXPLORE.value,
        script_path="/path/to/explore.py",
        step=1,
        total_steps=2,
        context_vars={"dimension": "naming"},
        free_form=False,  # Script mode - agent follows exact steps
    ),
]
```

### Fresh review mode (CoVe pattern)

```python
from skills.lib.workflow.formatters import format_qr_banner

# Iteration 1: initial review
banner = format_qr_banner(qr=QRState(iteration=1), qr_name="Plan Review")
# Output: "PLAN REVIEW: Review the work for issues."

# Iteration 2+: re-verify with fresh eyes (prevents confirmation bias)
banner = format_qr_banner(
    qr=QRState(iteration=2, failed=True, status="fail"),
    qr_name="Plan Review",
    fresh_review=True,
)
# Output: "PLAN REVIEW (Iteration 2, fresh review): Previous review found issues."
```

## Research Grounding

Workflow framework implements patterns from research literature:

**RE2 (Retrieval-Augmented Generation)**: format_resource() embeds reference materials inline so agent retrieves relevant context without external queries.

**CoVe (Chain-of-Verification)**: format_qr_banner() with fresh_review=True prevents confirmation bias by prompting QR agent to ignore prior findings. format_factored_verification_rationale() separates verification into independent sub-questions.

**Citations in docstrings**: Formatters document research grounding for future maintainers.
