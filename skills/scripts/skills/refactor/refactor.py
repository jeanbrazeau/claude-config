#!/usr/bin/env python3
"""
Refactor Skill - Category-based code smell detection and synthesis.

Five-phase workflow:
  1. Dispatch     - Launch parallel Explore agents (one per randomly selected category)
  2. Triage       - Review findings, structure as smells with IDs
  3. Cluster      - Group smells by shared root cause
  4. Contextualize - Extract user intent, prioritize issues
  5. Synthesize   - Generate actionable work items
"""

import argparse
import random
import re
import sys
from pathlib import Path

from skills.lib.workflow.formatters import (
    format_step_header,
    format_xml_mandate,
    format_current_action,
    format_invoke_after,
)
from skills.lib.workflow.types import FlatCommand


# Module paths for -m invocation
MODULE_PATH = "skills.refactor.refactor"
EXPLORE_MODULE_PATH = "skills.refactor.explore"

# Default number of code smell categories to explore per analysis run
DEFAULT_CATEGORY_COUNT = 10

# Path to conventions/code-quality/ directory
CONVENTIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "conventions" / "code-quality"


# =============================================================================
# Category Parser
# =============================================================================


def parse_categories() -> list[dict]:
    """Parse markdown files, return categories with line ranges.

    Returns:
        List of dicts with keys: file, name, start_line, end_line
    """
    categories = []
    for md_file in ["baseline.md", "coherence.md", "drift.md"]:
        path = CONVENTIONS_DIR / md_file
        if not path.exists():
            continue

        lines = path.read_text().splitlines()

        current_cat = None
        for i, line in enumerate(lines, 1):
            # Match: ## N. Category Name
            if match := re.match(r"^## \d+\. (.+)$", line):
                if current_cat:
                    current_cat["end_line"] = i - 1
                    categories.append(current_cat)
                current_cat = {
                    "file": md_file,
                    "name": match.group(1),
                    "start_line": i,
                }
        if current_cat:
            current_cat["end_line"] = len(lines)
            categories.append(current_cat)

    return categories


def select_categories(n: int = DEFAULT_CATEGORY_COUNT) -> list[dict]:
    """Randomly select N categories.

    Args:
        n: Number of categories to select (default 10)

    Returns:
        List of N randomly selected category dicts
    """
    all_cats = parse_categories()
    return random.sample(all_cats, min(n, len(all_cats)))


# =============================================================================
# XML Formatters (refactor-specific)
# =============================================================================


def format_parallel_dispatch(n: int = DEFAULT_CATEGORY_COUNT) -> str:
    """Format the parallel dispatch block for step 1."""
    selected = select_categories(n)

    lines = [f'<parallel_dispatch agent="Explore" count="{len(selected)}">']
    lines.append("  <instruction>")
    lines.append(f"    Launch {len(selected)} Explore sub-agents IN PARALLEL (single message, {len(selected)} Task tool calls).")
    lines.append("    Each agent explores ONE code smell category.")
    lines.append("  </instruction>")
    lines.append("")
    lines.append("  <model_selection>")
    lines.append("    Use HAIKU (default) for all explore agents.")
    lines.append("    Each agent has a narrow, well-defined task - cheap models work well.")
    lines.append("  </model_selection>")
    lines.append("")
    lines.append("  <template>")
    lines.append("    Explore the codebase for this code smell.")
    lines.append("")
    lines.append(f'    Start: <invoke working-dir=".claude/skills/scripts" cmd="python3 -m {EXPLORE_MODULE_PATH} --step 1 --total-steps 5 --category $CATEGORY_REF" />')
    lines.append("  </template>")
    lines.append("")
    lines.append("  <categories>")
    for cat in selected:
        ref = f"{cat['file']}:{cat['start_line']}-{cat['end_line']}"
        lines.append(f'    <category ref="{ref}">{cat["name"]}</category>')
    lines.append("  </categories>")
    lines.append("</parallel_dispatch>")
    return "\n".join(lines)


def format_expected_output(sections: dict[str, str]) -> str:
    """Render expected output block."""
    lines = ["<expected_output>"]
    for name, content in sections.items():
        lines.append(f'  <section name="{name}">')
        for line in content.split("\n"):
            lines.append(f"    {line}" if line else "")
        lines.append("  </section>")
    lines.append("</expected_output>")
    return "\n".join(lines)


# =============================================================================
# Step Definitions
# =============================================================================


STEPS = {
    1: {
        "title": "Dispatch",
        "brief": "Launch parallel Explore agents (one per randomly selected category)",
    },
    2: {
        "title": "Triage",
        "brief": "Structure smell findings with IDs for synthesis",
        "actions": [
            "REVIEW all smell_report outputs from Step 1.",
            "",
            "STRUCTURE each finding as a smell object with unique ID:",
            "",
            "OUTPUT FORMAT (JSON array):",
            "```json",
            "{",
            '  "smells": [',
            "    {",
            '      "id": "smell-1",',
            '      "type": "category from smell_report",',
            '      "location": "file:line-range",',
            '      "description": "issue description from finding",',
            '      "severity": "high|medium|low",',
            '      "evidence": "quoted code snippet"',
            "    }",
            "  ],",
            '  "smell_count": N,',
            '  "original_prompt": "user\'s original request (preserve exact wording)"',
            "}",
            "```",
            "",
            "PRESERVE the user's original prompt exactly - it will be used for intent extraction.",
            "",
            "Output the JSON, then proceed to clustering.",
        ],
    },
    3: {
        "title": "Cluster",
        "brief": "Group smells by shared root cause",
    },
    4: {
        "title": "Contextualize",
        "brief": "Extract user intent and prioritize issues",
    },
    5: {
        "title": "Synthesize",
        "brief": "Generate actionable work items",
    },
}


# =============================================================================
# Synthesis Prompts
# =============================================================================


def format_cluster_prompt() -> str:
    """Format the clustering prompt (Step 3)."""
    return """<task>
Given the smells from the previous step, identify which ones share root causes and should be addressed together.
</task>

<input>
Use the smells JSON from Step 2 output above.
</input>

<adaptive_analysis>
Check smell_count from the input:
- If <= 5: Quick relationship check, present as flat list unless obvious groupings emerge.
- If 6-20: Group by type + location proximity. Semantic analysis only for ambiguous cases.
- If > 20: Full multi-dimensional analysis.
</adaptive_analysis>

<analysis_process>
Walk through the smells systematically:

1. Categorize each smell by type and abstraction level.
   These levels are illustrative, not exhaustive -- use judgment for unlisted patterns:
   - structural: Architecture issues (e.g., circular deps, layering violations, god classes)
   - implementation: Code organization (e.g., long methods, duplication, feature envy)
   - surface: Cosmetic (e.g., naming, formatting, dead code, magic numbers)

   DOMAIN TRANSLATION: Before categorizing, consider how each level manifests in THIS project.
   What are the architectural patterns here? What code organization issues are common?
   Translate the abstract levels to project-specific concerns.

2. Identify groupings by shared characteristics

3. For each group, articulate the root cause - what underlying issue do these smells indicate?

4. Detect cross-cutting patterns: same theme across 3+ distinct locations

5. Handle overlaps: if a smell fits multiple groups, assign primary (highest confidence), mark others as related
</analysis_process>

<output_format>
Output JSON:
```json
{
  "issues": [
    {
      "id": "issue-1",
      "type": "pattern|cross_cutting|standalone",
      "root_cause": "Description of underlying issue",
      "smell_ids": ["smell-1", "smell-2"],
      "abstraction_level": "structural|implementation|surface",
      "scope": "file|module|system",
      "confidence": "STRONG|MODERATE",
      "related_issues": []
    }
  ],
  "analysis_notes": "Brief clustering rationale"
}
```
</output_format>

<edge_cases>
- No smells: Return empty issues array.
- No patterns found: Return all as standalone issues - this is valid.
- Single smell: Return as standalone, skip clustering.
</edge_cases>

Output the issues JSON, then proceed to contextualization."""


def format_contextualize_prompt() -> str:
    """Format the contextualization prompt (Step 4)."""
    return """<task>
Given the issues from the previous step and the user's original prompt, extract their intent and prioritize accordingly.
</task>

<input>
Use the issues JSON from Step 3 and original_prompt from Step 2.
</input>

<intent_extraction>
Read the original prompt again.

Extract quoted phrases that signal intent:
- Scope: "this file", "auth module", "entire codebase"
- Action: "quick cleanup", "refactor", "redesign", "fix"
- Thoroughness: "minimal changes", "comprehensive", "before shipping"
- Domain: "focus on security", "ignore tests", "API layer"

Rephrase: "The user wants to [action] at [scope] level, with [thoroughness] approach, focusing on [domain]."

Structure as:
```json
{
  "scope": "file|module|system|codebase",
  "action_type": "quick|refactor|redesign|investigate",
  "thoroughness": "minimal|balanced|comprehensive",
  "domain_focus": ["..."] or null
}
```
</intent_extraction>

<prioritization>
User phrasing directly influences promotion:
- quick -> promote surface issues, defer structural
- refactor -> promote implementation issues
- redesign -> promote structural issues
- Scope match -> boost priority
- Domain match -> boost priority

Mark each issue as:
- primary: Matches intent, should address
- deferred: Out of scope, noted for later
- appendix: Filtered but safety-notable (security/correctness >= MEDIUM, max 5)

If > 10 high-severity issues suppressed, flag as systemic warning.
</prioritization>

<dependencies>
For primary issues, identify:
- technical: Must complete A before B
- risk: Should complete A before B for safety
- obsolescence: Completing A may eliminate need for B
</dependencies>

<constraint_conflicts>
If intent conflicts with findings, use concrete examples:

NOT: "There's a conflict between your preferences and the issues."
USE: "Based on 'quick fixes': 7 items match (under 30min). 3 structural issues don't fit - defer or include?"
</constraint_conflicts>

<output_format>
Output JSON:
```json
{
  "intent": {
    "scope": "...",
    "action_type": "...",
    "thoroughness": "...",
    "domain_focus": ["..."],
    "rephrased": "The user wants to..."
  },
  "prioritized_issues": [
    {
      "id": "issue-1",
      "status": "primary|deferred|appendix",
      "relevance_rationale": "Why this status",
      "dependencies": { "technical": [], "risk": [], "obsolescence": [] }
    }
  ],
  "checkpoint_message": "Summary for user",
  "constraint_conflict": null or "Description with options"
}
```
</output_format>

<checkpoint>
PRESENT the checkpoint_message to the user. If there's a constraint_conflict, ask which direction they prefer before proceeding.

For conversational mode: pause here and let the user steer. They might say "focus on X" or "skip the structural issues" or "proceed with all".

For batch mode: proceed with primary issues.
</checkpoint>

<edge_cases>
- No intent signals: Exploratory mode - present top 5 by severity.
- All filtered: Empty primary, message about broadening.
- Contradictory signals: Surface conflict, ask for clarification.
</edge_cases>

Output the prioritized JSON and checkpoint_message, then proceed to synthesis."""


def format_synthesize_prompt() -> str:
    """Format the synthesis prompt (Step 5)."""
    return """<task>
Generate actionable work items from the prioritized issues. Each work item should be immediately executable with clear steps and verification.
</task>

<input>
Use the prioritized_issues (status=primary) from Step 4.
Use the action_type from the intent extraction.
</input>

<step_generation>
Generate steps appropriate to action_type:

quick:
- Specific edits with line references
- Single-file changes preferred
- Example: "Change line 45 from X to Y"

refactor:
- Approach outline with intermediate verification
- May span multiple files
- Example: "Extract method, update callers, verify tests"

redesign:
- Architectural changes with migration path
- Multi-phase approach
- Example: "Create interface, implement adapter, migrate consumers"
</step_generation>

<work_item_requirements>
Each work item needs:
- title: Specific (not "Fix X" but "Extract Y from Z to enable W")
- description: What this accomplishes
- affected_files: Specific files that change
- implementation_steps: Numbered, concrete steps
- verification_criteria: How to confirm it worked (tests, grep, behavior)
- dependencies: technical/risk/obsolescence
- estimated_complexity: low/medium/high
</work_item_requirements>

<example_generation>
BEFORE generating work items, create ONE example work item for THIS project:
  - Use actual file paths from the smells you analyzed
  - Use the project's language and conventions
  - Show the level of specificity expected

This self-generated example calibrates your output to the project context.
</example_generation>

<quality_criteria>
CORRECT work items have:
  - Specific title: "Extract X from Y to enable Z" (not "Fix X")
  - Concrete steps with file paths and line references where known
  - Verification that can be executed (test commands, grep patterns)
  - Realistic complexity estimate

INCORRECT work items have:
  - Vague titles: "Fix auth", "Clean up code"
  - Abstract steps: "Refactor the authentication"
  - No verification criteria
  - Missing file references
</quality_criteria>

<output_format>
Output JSON:
```json
{
  "work_items": [
    {
      "id": "work-1",
      "title": "...",
      "description": "...",
      "issue_ids": ["issue-1"],
      "smell_ids": ["smell-1", "smell-2"],
      "affected_files": ["..."],
      "implementation_steps": ["1. ...", "2. ..."],
      "verification_criteria": ["..."],
      "dependencies": { "technical": [], "risk": [], "obsolescence": [] },
      "estimated_complexity": "low|medium|high"
    }
  ],
  "recommended_sequence": ["work-1", "work-3", "work-2"],
  "summary": "Overview of the work"
}
```
</output_format>

<edge_cases>
- Single issue: Single work item, no sequencing.
- Circular deps: Flag warning, suggest breaking cycle.
- No code context: Approach-level steps, note line-specific needs code access.
</edge_cases>

Output the work_items JSON, then present the summary and recommended sequence to the user."""


# =============================================================================
# Output Formatting
# =============================================================================


def format_output(step: int, total_steps: int, n: int = DEFAULT_CATEGORY_COUNT) -> str:
    """Format output for display."""
    info = STEPS.get(step, STEPS[5])  # Default to last step
    is_complete = step >= total_steps

    parts = []

    # Step header
    parts.append(format_step_header("refactor", step, total_steps, info["title"]))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        parts.append(format_xml_mandate())
        parts.append("")

    # Build actions
    actions = []

    if step == 1:
        # Step 1: Parallel dispatch
        actions.append("IDENTIFY the scope from user's request:")
        actions.append("  - Could be: file(s), directory, subsystem, entire codebase")
        actions.append("")
        actions.append(format_parallel_dispatch(n))
        actions.append("")
        actions.append(f"WAIT for all {n} agents to complete before proceeding.")
        actions.append("")
        actions.append(format_expected_output({
            "Per category": "smell_report with severity (none/low/medium/high) and findings",
            "Format": "<smell_report> blocks from each Explore agent",
        }))
    elif step == 3:
        # Step 3: Cluster - use the prompt function
        actions.append(format_cluster_prompt())
    elif step == 4:
        # Step 4: Contextualize - use the prompt function
        actions.append(format_contextualize_prompt())
    elif step == 5:
        # Step 5: Synthesize - use the prompt function
        actions.append(format_synthesize_prompt())
    else:
        # Step 2 uses actions from STEPS dict
        if "actions" in info:
            actions.extend(info["actions"])

    parts.append(format_current_action(actions))
    parts.append("")

    # Invoke after / completion message
    if is_complete:
        parts.append("COMPLETE - Present work items to user with recommended sequence.")
        parts.append("")
        parts.append("The user can now:")
        parts.append("  - Execute work items in recommended order")
        parts.append("  - Ask to implement a specific work item")
        parts.append("  - Request adjustments to scope or approach")
    else:
        next_step = step + 1
        parts.append(format_invoke_after(
            FlatCommand(
                f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step {next_step} --total-steps {total_steps}" />'
            )
        ))

    return "\n".join(parts)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Skill - Category-based code smell detection and synthesis",
        epilog="Phases: dispatch -> triage -> cluster -> contextualize -> synthesize",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--n", type=int, default=DEFAULT_CATEGORY_COUNT,
                       help=f"Number of categories to explore (default: {DEFAULT_CATEGORY_COUNT})")
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 5:
        sys.exit("ERROR: --total-steps must be >= 5 (5 phases in workflow)")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps, args.n))


if __name__ == "__main__":
    main()
