"""Beads integration utilities for skills.

Provides optional beads (bd) issue tracking integration for skills that
execute in projects with beads initialized. Gracefully falls back when
beads is not available.

Usage:
    from skills.lib.beads import is_beads_available, create_issue, IssueType

    if is_beads_available():
        issue_id = create_issue(title="Feature X", issue_type=IssueType.FEATURE)
"""

import subprocess
import re
from dataclasses import dataclass
from enum import Enum


class IssueType(str, Enum):
    """Valid beads issue types."""
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    EPIC = "epic"
    CHORE = "chore"


class IssueStatus(str, Enum):
    """Valid beads issue statuses."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"


class DependencyType(str, Enum):
    """Valid beads dependency types."""
    BLOCKS = "blocks"
    RELATED = "related"
    PARENT_CHILD = "parent-child"
    DISCOVERED_FROM = "discovered-from"


@dataclass
class IssueId:
    """Value object wrapping a beads issue ID with validation."""
    id: str

    def __post_init__(self):
        """Validate issue ID format."""
        if not re.match(r'^[A-Z]+-\d+$', self.id):
            raise ValueError(f"Invalid issue ID format: {self.id}")

    def __str__(self) -> str:
        return self.id


@dataclass
class IssueData:
    """Structured issue data returned from beads queries."""
    id: str
    title: str
    priority: int | None = None
    issue_type: IssueType | None = None
    status: IssueStatus | None = None
    labels: list[str] | None = None
    deps: list[str] | None = None


def is_beads_available() -> bool:
    """Check if beads is available in current working directory.

    Returns:
        True if `bd list` succeeds, False otherwise
    """
    try:
        result = subprocess.run(
            ["bd", "list", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_issue(
    title: str,
    issue_type: IssueType | str = IssueType.TASK,
    description: str = "",
    priority: int = 2,
    labels: list[str] | None = None,
    deps: list[str | IssueId] | None = None,
) -> IssueId | None:
    """Create a beads issue and return its ID.

    Args:
        title: Issue title
        issue_type: IssueType enum or string (bug, feature, task, epic, chore)
        description: Issue description
        priority: 1 (high) to 3 (low), default 2
        labels: List of label strings
        deps: List of issue IDs (strings or IssueId objects) this depends on

    Returns:
        IssueId object or None if creation failed
    """
    if not is_beads_available():
        return None

    # Convert issue_type to string for command (handles both enum and str)
    type_str = issue_type.value if isinstance(issue_type, IssueType) else issue_type

    cmd = ["bd", "create", "--type", type_str, "--title", title]

    if description:
        cmd.extend(["--description", description])
    if priority:
        cmd.extend(["--priority", str(priority)])
    if labels:
        cmd.extend(["--labels", ",".join(labels)])
    if deps:
        for dep in deps:
            # Handle both string and IssueId types
            dep_str = str(dep) if isinstance(dep, IssueId) else dep
            cmd.extend(["--deps", dep_str])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            issue_id_str = _extract_issue_id(result.stdout)
            return IssueId(id=issue_id_str) if issue_id_str else None
    except subprocess.TimeoutExpired:
        pass

    return None


def update_status(issue_id: str | IssueId, status: IssueStatus | str) -> bool:
    """Update issue status.

    Args:
        issue_id: Issue ID string or IssueId object (e.g., "CFG-001")
        status: IssueStatus enum or string (open, in_progress, blocked, closed)

    Returns:
        True if update succeeded
    """
    if not is_beads_available():
        return False

    # Convert types to strings for command
    id_str = str(issue_id) if isinstance(issue_id, IssueId) else issue_id
    status_str = status.value if isinstance(status, IssueStatus) else status

    try:
        result = subprocess.run(
            ["bd", "update", id_str, "--status", status_str],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def close_issue(issue_id: str | IssueId, reason: str = "Completed") -> bool:
    """Close an issue.

    Args:
        issue_id: Issue ID string or IssueId object (e.g., "CFG-001")
        reason: Closure reason

    Returns:
        True if close succeeded
    """
    if not is_beads_available():
        return False

    # Convert to string for command
    id_str = str(issue_id) if isinstance(issue_id, IssueId) else issue_id

    try:
        result = subprocess.run(
            ["bd", "close", id_str, "--reason", reason],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def add_dependency(
    issue_id: str | IssueId,
    depends_on: str | IssueId,
    dep_type: DependencyType | str = DependencyType.BLOCKS
) -> bool:
    """Add a dependency between issues.

    Args:
        issue_id: The issue that has a dependency (string or IssueId)
        depends_on: The issue that blocks this one (string or IssueId)
        dep_type: DependencyType enum or string (blocks, related, parent-child, discovered-from)

    Returns:
        True if dependency added successfully
    """
    if not is_beads_available():
        return False

    # Convert all types to strings for command
    id_str = str(issue_id) if isinstance(issue_id, IssueId) else issue_id
    depends_str = str(depends_on) if isinstance(depends_on, IssueId) else depends_on
    type_str = dep_type.value if isinstance(dep_type, DependencyType) else dep_type

    try:
        result = subprocess.run(
            ["bd", "dep", id_str, depends_str, "--type", type_str],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def get_ready_issues(assignee: str | None = None, priority: int | None = None) -> list[IssueData]:
    """Get issues that are ready to work (no blockers).

    Args:
        assignee: Filter by assignee
        priority: Filter by priority

    Returns:
        List of IssueData objects with structured issue information
    """
    if not is_beads_available():
        return []

    cmd = ["bd", "ready"]
    if assignee:
        cmd.extend(["--assignee", assignee])
    if priority:
        cmd.extend(["--priority", str(priority)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return _parse_issue_list(result.stdout)
    except subprocess.TimeoutExpired:
        pass

    return []


def _extract_issue_id(output: str) -> str | None:
    """Extract issue ID from bd create output.

    Expected format: "Created issue CFG-001" or similar

    Returns:
        Issue ID string or None if not found
    """
    # Match pattern like CFG-001, PROJ-123, etc.
    match = re.search(r'\b([A-Z]+-\d+)\b', output)
    return match.group(1) if match else None


def _parse_issue_list(output: str) -> list[IssueData]:
    """Parse bd list/ready output into structured IssueData objects.

    This is a simple parser - beads may output in various formats.
    Adjust as needed based on actual bd output format.

    Returns:
        List of IssueData objects parsed from output
    """
    issues = []
    # Basic parsing - adjust based on actual bd output
    for line in output.split('\n'):
        match = re.match(r'\s*([A-Z]+-\d+)\s+(.+)', line)
        if match:
            issues.append(IssueData(
                id=match.group(1),
                title=match.group(2).strip(),
            ))
    return issues
