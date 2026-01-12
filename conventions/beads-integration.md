# Beads Integration

Optional issue tracking integration for skills that execute in projects with beads initialized.

## Purpose

Beads (bd) provides **persistent cross-session issue tracking** for:
- Multi-session features (planning → `/clear` → execution)
- Complex features with dependencies between milestones
- Technical debt tracking from refactor/analysis skills
- Work prioritization across multiple features

## When Skills Use Beads

Skills check for beads availability using `is_beads_available()` and gracefully fall back to TodoWrite when unavailable:

```python
from skills.lib.beads import is_beads_available

if is_beads_available():
    # Optional beads tracking
    create_issue(title="Feature X", issue_type="feature")
else:
    # Fallback to TodoWrite for in-session tracking
```

## Skill-Specific Integration

### Planner Skill

**Planning phase (step 5):**
- After writing plan, suggests creating feature issue
- Suggests creating milestone issues for each milestone
- Linking milestone dependencies via `bd dep`

**Execution phase (step 1):**
- Checks for existing feature/milestone issues
- Notes milestone IDs for status tracking

**Execution phase (step 3):**
- Optionally updates milestone status to `in_progress` when starting
- Optionally closes milestone issues when complete

**Execution phase (step 9 - retrospective):**
- Suggests closing parent feature issue if all milestones done
- Shows `bd ready` for remaining work

### Refactor Skill

**Not yet implemented.** Future integration:
- Create issues for MUST/SHOULD severity findings
- Label with `refactor`, `technical-debt`
- Priority based on severity + impact

### Codebase Analysis Skill

**Not yet implemented.** Future integration:
- Create issues for CRITICAL/HIGH findings
- Label with `security`, `architecture` as appropriate
- Link to specific file:line locations

## Beads vs TodoWrite

| Aspect | Beads (bd) | TodoWrite |
|--------|-----------|-----------|
| **Lifetime** | Persistent across sessions | Single conversation |
| **Survives /clear** | ✅ Yes | ❌ No |
| **Git-backed** | ✅ Yes | ❌ No |
| **Dependencies** | ✅ Yes (`bd dep`) | ❌ No |
| **Status tracking** | ✅ open, in_progress, blocked, closed | ❌ Limited |
| **Use case** | Cross-session work tracking | In-session task tracking |

**Hybrid strategy recommended:**

```
Beads (bd)              → Long-term, cross-session tracking
  ├─ Feature planning   → bd issue created
  ├─ Milestone tracking → bd issues per milestone
  ├─ Technical debt     → bd issues from refactor
  └─ Architecture gaps  → bd issues from analysis

TodoWrite               → Short-term, in-session tracking
  ├─ Debug statements   → Must clean up before session ends
  ├─ QR fix iterations  → Track fixes within review loop
  ├─ Current wave       → Which milestones are running now
  └─ Sub-task breakdown → Temporary task decomposition
```

## Initialization

Beads is initialized **per-project**, not in the config template:

```bash
cd ~/projects/my-app
bd init --prefix APP  # Creates .beads/ with APP-001, APP-002, etc.
```

Skills detect beads in the **current working directory** (the project being worked on), not the config directory.

## Common Commands

```bash
# Create issues
bd create --type feature --title "Add async logging" --priority 1
bd create --type task --title "M0: Configure NLog" --deps APP-001

# Update status
bd update APP-002 --status in_progress
bd close APP-002 "Milestone complete"

# Check work
bd ready                  # Show tasks with no blockers
bd list --status open     # Show all open issues
bd blocked                # Show blocked issues

# Dependencies
bd dep APP-003 APP-002    # APP-003 depends on APP-002
```

## Graceful Degradation

All beads integration is **optional**. Skills work identically when beads is not available:

1. **Detection**: `is_beads_available()` returns `False` if `bd list` fails
2. **Fallback**: Skills use TodoWrite for in-session tracking
3. **No errors**: No error messages if beads unavailable
4. **User choice**: Skills suggest but don't require beads usage

This allows the config to work across:
- Projects with beads initialized
- Projects using external issue tracking (JIRA, GitHub Issues)
- Projects with no issue tracking
- Quick one-off tasks

## Design Rationale

**Why optional?** Not all projects benefit from beads:
- Simple scripts or prototypes
- Projects with existing issue trackers
- One-session features

**Why suggest, not require?** Users should control tracking:
- Some prefer external tools
- Some find issue tracking overhead unnecessary
- Skills shouldn't force workflow changes

**Why per-project init?** Each project has unique needs:
- Different prefix conventions
- Different tracking granularity
- Some projects share trackers

## Library API

See `skills/lib/beads.py` for full API:

```python
# Availability check
is_beads_available() -> bool

# Issue operations
create_issue(title, issue_type="task", description="", ...) -> Optional[str]
update_status(issue_id, status) -> bool
close_issue(issue_id, reason="Completed") -> bool
add_dependency(issue_id, depends_on, dep_type="blocks") -> bool

# Queries
get_ready_issues(assignee=None, priority=None) -> list[dict]
```

All functions gracefully handle beads unavailability by returning `None` or `False`.
