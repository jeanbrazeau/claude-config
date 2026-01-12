#!/usr/bin/env python3
"""
Refactor Explore - Category-specific exploration for code smell detection.

Five-step workflow per category:
  1. Domain Context    - Identify project language/frameworks/structure
  2. Principle Extract - Step-back to extract principle + generate violation patterns
  3. Pattern Generate  - Translate abstract hints to project-specific grep patterns
  4. Search            - Execute patterns, document findings
  5. Synthesis         - Format findings with severity assessment
"""

import argparse
import sys
from pathlib import Path

from skills.lib.workflow.formatters import (
    format_xml_mandate,
    format_current_action,
    format_invoke_after,
)
from skills.lib.workflow.types import FlatCommand


MODULE_PATH = "skills.refactor.explore"
TOTAL_STEPS = 5

# Path to conventions/code-quality/ directory
CONVENTIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "conventions"
    / "code-quality"
)


# =============================================================================
# Category Loader
# =============================================================================


def load_category_block(category_ref: str) -> str:
    """Load category text block from file:start-end reference."""
    file_part, line_range = category_ref.split(":")
    start, end = map(int, line_range.split("-"))

    path = CONVENTIONS_DIR / file_part
    if not path.exists():
        sys.exit(f"ERROR: Category file not found: {path}")

    lines = path.read_text().splitlines()
    return "\n".join(lines[start - 1 : end])


# =============================================================================
# XML Formatters
# =============================================================================


def format_step_header(step: int, total: int, title: str, category_ref: str) -> str:
    """Render step header with category context."""
    return (
        f'<step_header script="explore" step="{step}" total="{total}" '
        f'category="{category_ref}">{title}</step_header>'
    )


def format_next_step(step: int, category_ref: str) -> str:
    """Format the invoke-after block for next step."""
    return format_invoke_after(
        FlatCommand(
            f'<invoke working-dir=".claude/skills/scripts" '
            f'cmd="python3 -m {MODULE_PATH} --step {step} --total-steps {TOTAL_STEPS} '
            f'--category {category_ref}" />'
        )
    )


# =============================================================================
# Step 1: Domain Context
# =============================================================================


def format_step_1(category_ref: str) -> str:
    """Step 1: Identify project domain context."""
    actions = [
        "DOMAIN CONTEXT ANALYSIS:",
        "",
        "Before detecting smells, understand the project's technical context.",
        "This enables translating abstract patterns to project-specific ones.",
        "",
        "IDENTIFY (brief exploration, ~30 seconds):",
        "",
        "  1. LANGUAGE: Primary programming language(s)",
        "     Check: file extensions, shebang lines",
        "",
        "  2. FRAMEWORKS: Key frameworks/libraries",
        "     Check: package.json, requirements.txt, go.mod, Cargo.toml, pom.xml",
        "     Note: major frameworks (React, Django, Spring, etc.)",
        "",
        "  3. CONVENTIONS: Naming patterns used in this codebase",
        "     Check: a few source files for naming style",
        "     Note: camelCase vs snake_case, common suffixes (Service, Handler, etc.)",
        "",
        "OUTPUT (required):",
        '<domain_context>',
        '  <language>primary language</language>',
        '  <frameworks>framework1, framework2</frameworks>',
        '  <conventions>naming patterns observed</conventions>',
        '</domain_context>',
        "",
        "Keep this brief. Accuracy matters more than completeness.",
    ]

    parts = [
        format_step_header(1, TOTAL_STEPS, "Domain Context", category_ref),
        "",
        format_xml_mandate(),
        "",
        format_current_action(actions),
        "",
        format_next_step(2, category_ref),
    ]
    return "\n".join(parts)


# =============================================================================
# Step 2: Principle + Violation Patterns
# =============================================================================


def format_step_2(category_ref: str) -> str:
    """Step 2: Extract principle and generate violation patterns."""
    category_block = load_category_block(category_ref)

    actions = [
        # Meta-instruction: Frame examples as exemplars
        "<interpretation>",
        "The violations listed below are ILLUSTRATIVE PATTERNS, not an exhaustive checklist.",
        "Detect ANY code violating the underlying <principle>, including unlisted patterns.",
        "</interpretation>",
        "",
        "<smell_category>",
        category_block,
        "</smell_category>",
        "",
        "STEP-BACK: PRINCIPLE EXTRACTION",
        "",
        "Read the category definition. Extract:",
        "  - The PRINCIPLE (the 'why' that unifies all violations)",
        "  - The detection question (what to ask about each code fragment)",
        "  - The severity threshold (when to flag)",
        "",
        "ANALOGICAL GENERATION - VIOLATION PATTERNS:",
        "",
        "Using your domain context from Step 1, identify 2-3 ADDITIONAL violation patterns",
        "that would violate the SAME principle in THIS project's domain:",
        "",
        "  - What does this smell look like in [your language/framework]?",
        "  - What project-specific idioms might violate this principle?",
        "  - What framework-specific anti-patterns apply?",
        "",
        "If no additional patterns emerge, proceed with listed ones.",
        "",
        "OUTPUT (required):",
        '<principle_analysis>',
        '  <principle>the core principle in one sentence</principle>',
        '  <detection_question>what to ask about each code fragment</detection_question>',
        '  <threshold>when to flag vs ignore</threshold>',
        '  <violation_patterns>',
        '    <pattern source="listed">pattern from category definition</pattern>',
        '    <pattern source="generated">project-specific pattern you identified</pattern>',
        '    <!-- include all patterns: listed + generated -->',
        '  </violation_patterns>',
        '</principle_analysis>',
    ]

    parts = [
        format_step_header(2, TOTAL_STEPS, "Principle + Violations", category_ref),
        "",
        format_current_action(actions),
        "",
        format_next_step(3, category_ref),
    ]
    return "\n".join(parts)


# =============================================================================
# Step 3: Search Pattern Generation
# =============================================================================


def format_step_3(category_ref: str) -> str:
    """Step 3: Generate project-specific grep patterns."""
    actions = [
        "SEARCH PATTERN GENERATION:",
        "",
        "The <grep-hints> in the category definition are ABSTRACT EXEMPLARS.",
        "They represent what to look for in a generic codebase.",
        "",
        "TRANSLATE to this project's domain:",
        "",
        "For EACH violation pattern (from Step 2), generate grep-able patterns:",
        "",
        "  - What would 'Manager' look like here? (Service, Repository, Store, Handler...)",
        "  - What naming conventions does this project use?",
        "  - What are the framework-specific equivalents?",
        "",
        "Examples of translation:",
        "  Abstract: 'Manager, Handler, Utils'",
        "  Python/Flask: 'Service, Repository, Blueprint, helpers'",
        "  Go: 'Handler, Store, Controller, util'",
        "  React: 'Container, Provider, HOC, utils'",
        "",
        "OUTPUT (required):",
        '<search_patterns>',
        '  <pattern reason="why this indicates the smell">regex_or_literal</pattern>',
        '  <pattern reason="...">...</pattern>',
        '  <!-- 5-10 patterns, project-specific -->',
        '</search_patterns>',
        "",
        "These patterns will be used for Grep in Step 4.",
    ]

    parts = [
        format_step_header(3, TOTAL_STEPS, "Pattern Generation", category_ref),
        "",
        format_current_action(actions),
        "",
        format_next_step(4, category_ref),
    ]
    return "\n".join(parts)


# =============================================================================
# Step 4: Search
# =============================================================================


def format_step_4(category_ref: str) -> str:
    """Step 4: Execute search and document findings."""
    actions = [
        "SEARCH EXECUTION:",
        "",
        "Using the patterns from Step 3, search the codebase:",
        "",
        "  1. Use Glob to find relevant files in scope",
        "  2. Use Grep with each pattern from <search_patterns>",
        "  3. Use Read to examine suspicious matches",
        "  4. Apply the detection question from Step 2 to each match",
        "",
        "CROSS-FILE ANALYSIS:",
        "",
        "  5. After finding an issue, Grep for similar patterns in OTHER files",
        "  6. Note when patterns appear in 3+ locations (abstraction candidates)",
        "",
        "CALIBRATION:",
        "",
        "  - Finding zero issues is a valid outcome. Do not force findings.",
        "  - Flag only when evidence is clear. Ambiguous cases are not findings.",
        "  - Apply the <threshold> from Step 2 - if exception applies, don't flag.",
        "",
        "OUTPUT (required):",
        '<findings>',
        '  <finding location="file:line-range">',
        '    <evidence>quoted code (2-5 lines)</evidence>',
        '    <issue>what violates the principle</issue>',
        '    <similar_locations>file2:line, file3:line OR "Unique"</similar_locations>',
        '  </finding>',
        '  <!-- repeat for each finding -->',
        '</findings>',
        "",
        "Document findings. Do NOT propose solutions yet.",
    ]

    parts = [
        format_step_header(4, TOTAL_STEPS, "Search", category_ref),
        "",
        format_current_action(actions),
        "",
        format_next_step(5, category_ref),
    ]
    return "\n".join(parts)


# =============================================================================
# Step 5: Synthesis
# =============================================================================


def format_step_5(category_ref: str) -> str:
    """Step 5: Synthesize findings into smell report."""
    actions = [
        "SYNTHESIZE findings from Step 4 into final report.",
        "",
        "OUTPUT FORMAT (strict):",
        "",
        '<smell_report category="$CATEGORY_NAME" severity="high|medium|low|none" count="N">',
        '  <finding location="file:line-range" severity="high|medium|low">',
        '    <evidence>quoted code (2-5 lines max)</evidence>',
        '    <issue>what is wrong (one sentence)</issue>',
        '  </finding>',
        '  <!-- repeat for each finding -->',
        '</smell_report>',
        "",
        "SEVERITY LEVELS:",
        "  HIGH: Blocks maintainability, affects multiple areas",
        "  MEDIUM: Causes friction, localized impact",
        "  LOW: Minor annoyance, cosmetic",
        "  NONE: No issues found (empty findings)",
        "",
        "Extract $CATEGORY_NAME from the ## heading in the category block.",
        "",
        "OUTPUT your smell_report now.",
    ]

    parts = [
        format_step_header(5, TOTAL_STEPS, "Synthesis", category_ref),
        "",
        format_current_action(actions),
        "",
        "COMPLETE - Return smell_report to orchestrator.",
    ]
    return "\n".join(parts)


# =============================================================================
# Output Router
# =============================================================================


def format_output(step: int, category_ref: str) -> str:
    """Route to appropriate step formatter."""
    formatters = {
        1: format_step_1,
        2: format_step_2,
        3: format_step_3,
        4: format_step_4,
        5: format_step_5,
    }
    formatter = formatters.get(step)
    if not formatter:
        sys.exit(f"ERROR: Unknown step {step}")
    return formatter(category_ref)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Explore - Category-specific code smell detection",
        epilog=f"Steps: context -> principle -> patterns -> search -> synthesis ({TOTAL_STEPS} total)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        help="Category reference as file:startline-endline (e.g., baseline.md:5-13)",
    )

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps != TOTAL_STEPS:
        sys.exit(f"ERROR: --total-steps must be {TOTAL_STEPS}")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    # Validate category format
    if ":" not in args.category or "-" not in args.category.split(":")[1]:
        sys.exit("ERROR: --category must be in format file.md:start-end")

    print(format_output(args.step, args.category))


if __name__ == "__main__":
    main()
