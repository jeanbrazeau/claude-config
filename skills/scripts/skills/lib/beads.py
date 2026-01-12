"""Beads integration utilities for skills.

Provides optional beads (bd) issue tracking integration for skills that
execute in projects with beads initialized. Gracefully falls back when
beads is not available.

Usage:
    from skills.lib.beads import is_beads_available, create_issue

    if is_beads_available():
        issue_id = create_issue(title="Feature X", issue_type="feature")
"""

import subprocess
import re
from typing import Optional


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
    issue_type: str = "task",
    description: str = "",
    priority: int = 2,
    labels: list[str] = None,
    deps: list[str] = None,
) -> Optional[str]:
    """Create a beads issue and return its ID.

    Args:
        title: Issue title
        issue_type: bug, feature, task, epic, chore
        description: Issue description
        priority: 1 (high) to 3 (low), default 2
        labels: List of label strings
        deps: List of issue IDs this depends on

    Returns:
        Issue ID (e.g., "CFG-001") or None if creation failed
    """
    if not is_beads_available():
        return None

    cmd = ["bd", "create", "--type", issue_type, "--title", title]

    if description:
        cmd.extend(["--description", description])
    if priority:
        cmd.extend(["--priority", str(priority)])
    if labels:
        cmd.extend(["--labels", ",".join(labels)])
    if deps:
        for dep in deps:
            cmd.extend(["--deps", dep])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return _extract_issue_id(result.stdout)
    except subprocess.TimeoutExpired:
        pass

    return None


def update_status(issue_id: str, status: str) -> bool:
    """Update issue status.

    Args:
        issue_id: Issue ID (e.g., "CFG-001")
        status: open, in_progress, blocked, closed

    Returns:
        True if update succeeded
    """
    if not is_beads_available():
        return False

    try:
        result = subprocess.run(
            ["bd", "update", issue_id, "--status", status],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def close_issue(issue_id: str, reason: str = "Completed") -> bool:
    """Close an issue.

    Args:
        issue_id: Issue ID (e.g., "CFG-001")
        reason: Closure reason

    Returns:
        True if close succeeded
    """
    if not is_beads_available():
        return False

    try:
        result = subprocess.run(
            ["bd", "close", issue_id, "--reason", reason],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def add_dependency(issue_id: str, depends_on: str, dep_type: str = "blocks") -> bool:
    """Add a dependency between issues.

    Args:
        issue_id: The issue that has a dependency
        depends_on: The issue that blocks this one
        dep_type: blocks, related, parent-child, discovered-from

    Returns:
        True if dependency added successfully
    """
    if not is_beads_available():
        return False

    try:
        result = subprocess.run(
            ["bd", "dep", issue_id, depends_on, "--type", dep_type],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def get_ready_issues(assignee: str = None, priority: int = None) -> list[dict]:
    """Get issues that are ready to work (no blockers).

    Args:
        assignee: Filter by assignee
        priority: Filter by priority

    Returns:
        List of issue dicts with keys: id, title, priority, type
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


def _extract_issue_id(output: str) -> Optional[str]:
    """Extract issue ID from bd create output.

    Expected format: "Created issue CFG-001" or similar
    """
    # Match pattern like CFG-001, PROJ-123, etc.
    match = re.search(r'\b([A-Z]+-\d+)\b', output)
    return match.group(1) if match else None


def _parse_issue_list(output: str) -> list[dict]:
    """Parse bd list/ready output into structured data.

    This is a simple parser - beads may output in various formats.
    Adjust as needed based on actual bd output format.
    """
    issues = []
    # Basic parsing - adjust based on actual bd output
    for line in output.split('\n'):
        match = re.match(r'\s*([A-Z]+-\d+)\s+(.+)', line)
        if match:
            issues.append({
                'id': match.group(1),
                'title': match.group(2).strip(),
            })
    return issues
