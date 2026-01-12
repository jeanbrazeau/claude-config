#!/usr/bin/env python3
"""
Prompt Engineer Skill - Scope-adaptive prompt optimization workflow.

Architecture:
  - Per-scope WorkflowDefinition with shared Step constants
  - Factory functions for reusable action fragments
  - Step count derived from scope (no --total-steps)

Scopes:
  - single-prompt: One prompt file, general optimization
  - ecosystem: Multiple related prompts that interact
  - greenfield: No existing prompt, designing from requirements
  - problem: Existing prompt(s) with specific issue to fix

Research grounding:
  - Self-Refine (Madaan 2023): Separate feedback from refinement
  - CoVe (Dhuliawala 2023): Factored verification with OPEN questions
"""

import argparse
import sys

from skills.lib.workflow.types import (
    Step,
    LinearRouting,
    TerminalRouting,
    WorkflowDefinition,
)


# =============================================================================
# Action Factory Functions
# =============================================================================


def technique_review_actions(for_ecosystem: bool = False) -> list[str]:
    """Systematic technique review - shared across scopes in Plan step."""
    base = [
        "SYSTEMATIC TECHNIQUE REVIEW:",
        "  For each technique in the Technique Selection Guide:",
        "  1. QUOTE the trigger condition from the table",
        "  2. QUOTE text from the target prompt that matches (or state 'No match')",
        "  3. Verdict: APPLICABLE (with both quotes) or NOT APPLICABLE",
        "  - Pay attention to 'Any task' triggers (foundational techniques)",
    ]
    if for_ecosystem:
        base.append("  - Note techniques that apply to multiple prompts")
    return base


def change_format_actions(entity: str = "CHANGE") -> list[str]:
    """Change format template - entity is CHANGE, FIX, or SECTION."""
    lines = [
        f"Format each {entity.lower()}:",
        f"  === {entity} N: [title] ===",
        "  Line: [numbers]",
        '  Technique: [name] | Trigger: "[quoted]" | Effect: [quoted]',
        "  BEFORE: [original]",
        "  AFTER: [modified]",
    ]
    if entity == "CHANGE":
        lines.append("  TRADEOFF: [downside or None]")
    return lines


def change_presentation_actions() -> list[str]:
    """Change presentation format for Execute steps - shows before/after for each change."""
    return [
        "PRESENT CHANGES MADE:",
        "",
        "For EACH change applied, show:",
        "  === CHANGE N: [title] ===",
        "  Location: [file:lines]",
        "  BEFORE:",
        "  ```",
        "  [original text]",
        "  ```",
        "  AFTER:",
        "  ```",
        "  [modified text]",
        "  ```",
        "",
        "Then present the complete modified prompt(s).",
    ]


def anti_pattern_audit_actions(
    target: str = "modified prompt",
    context: str | None = None,
) -> list[str]:
    """Anti-pattern audit - used in Execute step."""
    base = [
        f"ANTI-PATTERN FINAL AUDIT against {target}:",
        "",
        "Check each anti-pattern from the reference:",
        "  [ ] Hedging Spiral: Does it encourage hesitation?",
        "  [ ] Everything-Is-Critical: Are emphasis markers overused?",
        "  [ ] Implicit Category Trap: Are categories explicit?",
        "  [ ] Negative Instruction Trap: Are directives affirmative?",
    ]
    if context in ("SKILL", "SUB-AGENT", "COMPONENT"):
        base.extend([
            "",
            "CONTEXT-SPECIFIC (non-STANDALONE):",
            "  [ ] Context Mismatch: Does it have <system> or identity setup?",
            "      If YES -> FAIL: Remove wrapper/identity.",
        ])
    return base


def integration_check_actions(checks: list[str]) -> list[str]:
    """Integration checks wrapper."""
    return ["INTEGRATION CHECKS:"] + [f"  - {c}" for c in checks]


def ecosystem_relationship_table() -> list[str]:
    """Ecosystem-only: map cross-prompt relationships."""
    return [
        "Create interaction table:",
        "  | Prompt | File:Lines | Receives From | Sends To | Shared Terms |",
        "  |--------|------------|---------------|----------|--------------|",
        "",
        "For each prompt, identify:",
        "  - Input sources (which prompts/systems feed it)",
        "  - Output consumers (which prompts/systems consume its output)",
        "  - Terminology that MUST be consistent across prompts",
    ]


def understand_actions_ecosystem() -> list[str]:
    """Semantic understanding phase for ecosystem scope."""
    return [
        "ARTICULATE semantic understanding before optimization.",
        "",
        "<system_understanding>",
        "  What is this workflow accomplishing end-to-end?",
        "  What enters the system? What does it produce?",
        "  What invariants must be maintained across components?",
        "</system_understanding>",
        "",
        "<prompt_understanding>",
        "  For EACH prompt, answer:",
        "  - What does this prompt ACCOMPLISH (purpose, not description)?",
        "  - Why is it positioned HERE in the sequence?",
        "  - What would BREAK if this prompt were removed?",
        "</prompt_understanding>",
        "",
        "<handoff_understanding>",
        "  For EACH delegation (A -> B), answer:",
        "  - What is B's BOUNDED responsibility? (specific task, not 'help')",
        "  - What is the MINIMUM information B needs to accomplish that?",
        "  - What does B ALREADY KNOW from its own context?",
        "  - What must NOT cross this boundary? Why?",
        "    (orchestrator internals, workflow steps, other components' state)",
        "</handoff_understanding>",
        "",
        "INVERT THE DEFAULT QUESTION:",
        "  Ask 'what is the MINIMUM B needs?' not 'what might help B?'",
        "",
        "CONTRASTIVE EXAMPLES:",
        "",
        "<example type='CORRECT'>",
        "  SKILL.md: 'Invoke the script. The script IS the workflow.'",
        "  WHY: Main agent delegates completely. No internals exposed.",
        "</example>",
        "<example type='INCORRECT'>",
        "  SKILL.md: 'Invoke the script. It has 6 steps: 1. Triage...'",
        "  WHY: Main agent doesn't need workflow internals.",
        "</example>",
        "",
        "<example type='CORRECT'>",
        "  Sub-agent: 'Execute step 1. <invoke cmd=\"...--step 1\" />'",
        "  WHY: Sub-agent needs only its step instructions.",
        "</example>",
        "<example type='INCORRECT'>",
        "  Sub-agent: 'Execute step 1. There are 8 steps: 1. Context...'",
        "  WHY: Sub-agent discovers workflow during execution. Overview is noise.",
        "</example>",
    ]


def verify_understanding_actions() -> list[str]:
    """Counterfactual verification of understanding claims."""
    return [
        "TEST understanding with counterfactual questions (OPEN, not yes/no).",
        "",
        "For EACH handoff (A -> B):",
        "  Q: DESCRIBE what could be REMOVED from this handoff without breaking B.",
        "  A: [list specific items currently included but not necessary]",
        "",
        "  Q: EXPLAIN what would fail and HOW if we added orchestrator internals",
        "     (workflow steps, state, other components) to this handoff.",
        "  A: [describe mechanism: confusion, coupling, scope creep, etc.]",
        "",
        "For the ECOSYSTEM:",
        "  Q: If component X were removed, WHICH components break and WHY?",
        "  A: [trace dependencies based on your understanding]",
        "",
        "CONSISTENCY CHECK:",
        "  Compare answers to <handoff_understanding>.",
        "  Revise understanding if inconsistent.",
    ]


def understand_actions_simple() -> list[str]:
    """Lighter semantic understanding for single-prompt/problem scopes."""
    return [
        "ARTICULATE what this prompt accomplishes:",
        "",
        "<purpose>",
        "  What is the high-level goal of this prompt?",
        "  What inputs does it expect?",
        "  What outputs should it produce?",
        "  What does SUCCESS look like?",
        "</purpose>",
        "",
        "<boundaries>",
        "  If this prompt delegates to sub-agents or other components:",
        "  - What is each recipient's bounded responsibility?",
        "  - What is the MINIMUM each recipient needs?",
        "  - What should NOT be passed to recipients? Why?",
        "  If no delegation exists, state: 'No delegation boundaries.'",
        "</boundaries>",
    ]


def handoff_minimalism_test() -> list[str]:
    """Test for handoff minimalism in PLAN phase."""
    return [
        "  - For each handoff: is it MINIMAL?",
        "    REJECT changes that add information the receiver doesn't need.",
        "    REJECT changes that leak orchestrator internals.",
        "",
        "  HANDOFF MINIMALISM TEST for each proposed change:",
        "    Ask: 'Would the receiver need to change if this internal changed?'",
        "    NO -> creates coupling without benefit -> EXCLUDE",
        "    YES -> necessary information -> INCLUDE",
    ]


# =============================================================================
# READ Specifications (injected at PLAN step - varies by scope)
# =============================================================================

# Maps scope -> (step_number, read_specs)
READ_SPECS: dict[str, tuple[int, list[str]]] = {
    "single-prompt": (4, [  # Plan is step 4
        "references/prompt-engineering-single-turn.md",
        "  -> Extract: Technique Selection Guide table",
        "  -> For each technique: note Trigger Condition column",
        "If multi-turn patterns detected: also read multi-turn reference.",
    ]),
    "ecosystem": (5, [  # Plan is step 5
        "references/prompt-engineering-single-turn.md",
        "references/prompt-engineering-multi-turn.md (always for ecosystem)",
        "  -> Extract: Technique Selection Guide from each",
        "  -> For each technique: note Trigger Condition column",
        "If orchestration or human gates: also read subagents/hitl refs.",
    ]),
    "greenfield": (4, [  # Design is step 4
        "references/prompt-engineering-single-turn.md",
        "  -> Extract: Technique Selection Guide table",
        "  -> For each technique: note Trigger Condition column",
        "If multi-turn architecture chosen: also read multi-turn reference.",
    ]),
    "problem": (4, [  # Target Fix is step 4
        "references/prompt-engineering-single-turn.md",
        "  -> Extract: Technique Selection Guide table",
        "  -> Focus on techniques matching the problem class",
        "If problem involves multi-turn patterns: also read multi-turn reference.",
    ]),
}


# =============================================================================
# Shared Step Constants
# =============================================================================

STEP_TRIAGE = Step(
    title="Triage",
    actions=[
        "EXAMINE the input and request:",
        "",
        "  FILES PROVIDED:",
        "    - None: likely GREENFIELD",
        "    - Single file with prompt: likely SINGLE-PROMPT",
        "    - Multiple related files: likely ECOSYSTEM",
        "",
        "  REQUEST TYPE:",
        "    - General optimization ('improve this'): SINGLE-PROMPT or ECOSYSTEM",
        "    - Specific problem ('fix X', 'it does Y wrong'): PROBLEM",
        "    - Design request ('I want X to do Y'): GREENFIELD",
        "",
        "DETERMINE SCOPE (use boundary tests):",
        "  SINGLE-PROMPT: One file + 'improve/optimize' request",
        "    Boundary: If 2+ files interact -> ECOSYSTEM",
        "  ECOSYSTEM: Multiple files with shared terminology or data flow",
        "    Boundary: If no interaction between files -> multiple SINGLE-PROMPT",
        "  GREENFIELD: No existing prompt + 'create/design/build' request",
        "    Boundary: If modifying existing -> SINGLE-PROMPT or PROBLEM",
        "  PROBLEM: Existing prompt + specific failure described",
        "    Boundary: If no specific failure -> SINGLE-PROMPT or ECOSYSTEM",
        "",
        "OUTPUT:",
        "  SCOPE: [single-prompt | ecosystem | greenfield | problem]",
        "  RATIONALE: [why this scope fits]",
    ],
    routing=LinearRouting(),
    phase="triage",
)


STEP_REFINE = Step(
    title="Refine",
    actions=[
        "VERIFY each proposed technique (factored verification):",
        "",
        "  For each technique you claimed APPLICABLE:",
        "  1. Close your proposal. Answer from reference ONLY:",
        "     Q: 'What is the EXACT trigger condition for [technique]?'",
        "  2. Close the reference. Answer from target prompt ONLY:",
        "     Q: 'What text appears at line [N]?'",
        "  3. Compare: Does quoted text match quoted trigger?",
        "",
        "  Cross-check: CLAIMED vs VERIFIED",
        "    CONSISTENT -> keep",
        "    INCONSISTENT -> revise or remove",
        "",
        "SPOT-CHECK dismissed techniques:",
        "  Pick 3 marked NOT APPLICABLE",
        "  Verify triggers truly don't match",
        "",
        "UPDATE proposals based on verification.",
        "",
        "CONTEXT-CORRECTNESS VERIFICATION (for greenfield/problem scopes):",
        "  If execution context was identified (STANDALONE/SKILL/SUB-AGENT/COMPONENT):",
        "",
        "  Q: What is the execution context for this prompt?",
        "  A: [answer from Step 2/Assess]",
        "",
        "  Q: Does the draft contain <system> wrapper or identity setup?",
        "  A: [quote from draft or 'None']",
        "",
        "  Q: Should this execution context have <system>/identity?",
        "  A: STANDALONE -> yes. SKILL/SUB-AGENT/COMPONENT -> no.",
        "",
        "  If INCONSISTENT: flag for revision before Approve step.",
    ],
    routing=LinearRouting(),
    phase="verify",
)


STEP_APPROVE = Step(
    title="Approve",
    actions=[
        "Present using this format:",
        "",
        "PROPOSED CHANGES",
        "================",
        "",
        "| # | Location | Opportunity | Technique | Risk |",
        "|---|----------|-------------|-----------|------|",
        "",
        "Then each change in detail",
        "",
        "VERIFICATION SUMMARY:",
        "  - Changes verified: N",
        "  - Changes revised: M",
        "  - Changes removed: K",
        "",
        "ANTI-PATTERNS CHECKED:",
        "  From Anti-Patterns section of each reference read:",
        "  - List each by name",
        "  - For each: [OK] or [FOUND: description]",
        "",
        "",
        "CRITICAL: STOP. Do NOT proceed to Execute step.",
        "Wait for explicit user approval before continuing.",
    ],
    routing=LinearRouting(),
    phase="approve",
)


# =============================================================================
# Per-Scope Step Definitions
# =============================================================================

SINGLE_PROMPT_STEPS: dict[int, Step] = {
    1: STEP_TRIAGE,
    2: Step(
        title="Assess",
        actions=[
            "READ the prompt file. Classify complexity:",
            "  SIMPLE: <20 lines, single purpose, no conditionals",
            "  COMPLEX: multiple sections, conditionals, tool orchestration",
            "",
            "Document OPERATING CONTEXT:",
            "  - Interaction: single-shot or conversational?",
            "  - Agent type: tool-use, coding, analysis, general?",
            "  - Failure modes: what goes wrong when this fails?",
        ],
        routing=LinearRouting(),
        phase="assess",
    ),
    3: Step(
        title="Understand",
        actions=[
            *understand_actions_simple(),
        ],
        routing=LinearRouting(),
        phase="understand",
    ),
    4: Step(
        title="Plan",
        actions=[
            "BLIND identification of opportunities (quote line evidence):",
            "  List as 'Lines X-Y: [issue]'",
            "",
            *technique_review_actions(),
            "",
            *change_format_actions("CHANGE"),
            "",
            "Include TECHNIQUE DISPOSITION summary.",
        ],
        routing=LinearRouting(),
        phase="plan",
    ),
    5: STEP_REFINE,
    6: STEP_APPROVE,
    7: Step(
        title="Execute",
        actions=[
            "Apply each approved change to the prompt file.",
            "",
            *integration_check_actions([
                "Cross-section references correct?",
                "Terminology consistent?",
                "Priority markers not overused? (max 2-3 CRITICAL/NEVER)",
            ]),
            "",
            *anti_pattern_audit_actions("modified prompt"),
            "",
            *change_presentation_actions(),
        ],
        routing=TerminalRouting(),
        phase="execute",
    ),
}


ECOSYSTEM_STEPS: dict[int, Step] = {
    1: STEP_TRIAGE,
    2: Step(
        title="Assess",
        actions=[
            "READ all prompt-containing files in scope.",
            "",
            "MAP the ecosystem:",
            "  - List each prompt with location (file:lines)",
            "  - Identify relationships: orchestrator, subagent, shared-context",
            "  - Note terminology that should be consistent across prompts",
            "",
            *ecosystem_relationship_table(),
            "",
            "For EACH prompt, document:",
            "  - Purpose and role in the ecosystem",
            "  - What it receives from / passes to other prompts",
            "  - Complexity classification",
        ],
        routing=LinearRouting(),
        phase="assess",
    ),
    3: Step(
        title="Understand",
        actions=[
            *understand_actions_ecosystem(),
        ],
        routing=LinearRouting(),
        phase="understand",
    ),
    4: Step(
        title="Verify Understanding",
        actions=[
            *verify_understanding_actions(),
        ],
        routing=LinearRouting(),
        phase="verify_understanding",
    ),
    5: Step(
        title="Plan",
        actions=[
            "FOR EACH PROMPT - identify opportunities:",
            "  List as 'File:Lines X-Y: [issue]'",
            "",
            "FOR THE ECOSYSTEM - identify cross-prompt issues:",
            "  Using your interaction table AND your <handoff_understanding>:",
            "  - For each Shared Term: check consistency across listed prompts",
            "  - For each Receives From/Sends To pair: check handoff clarity",
            *handoff_minimalism_test(),
            "  - Conflicting instructions",
            "  - Redundant specifications",
            "  List as 'ECOSYSTEM: [issue across File1, File2]'",
            "",
            *technique_review_actions(for_ecosystem=True),
            "",
            *change_format_actions("CHANGE"),
            "Note which changes affect single file vs multiple.",
        ],
        routing=LinearRouting(),
        phase="plan",
    ),
    6: STEP_REFINE,
    7: STEP_APPROVE,
    8: Step(
        title="Execute",
        actions=[
            "Apply changes to each file.",
            "",
            "ECOSYSTEM INTEGRATION CHECKS:",
            "  - Terminology aligned across all files?",
            "  - Handoffs clear and consistent?",
            "  - No conflicting instructions introduced?",
            "",
            *anti_pattern_audit_actions("ALL modified prompts"),
            "",
            *change_presentation_actions(),
        ],
        routing=TerminalRouting(),
        phase="execute",
    ),
}


GREENFIELD_STEPS: dict[int, Step] = {
    1: STEP_TRIAGE,
    2: Step(
        title="Assess Requirements",
        actions=[
            "UNDERSTAND requirements:",
            "  - What task should the prompt accomplish?",
            "  - What inputs will it receive?",
            "  - What outputs should it produce?",
            "  - What constraints exist? (length, format, tone)",
            "",
            "DETERMINE execution context (CRITICAL - affects scaffold):",
            "  STANDALONE: Full system prompt with complete control",
            "    -> Prompt IS the system message, can define identity/role",
            "  SKILL: Injected into existing agent (e.g., Claude Code skill)",
            "    -> NO <system> wrapper, NO identity setup, task-focused",
            "  SUB-AGENT: Task instruction passed to delegated agent",
            "    -> Bounded task description, minimal context, NO workflow overview",
            "  COMPONENT: Fragment composing with other prompts",
            "    -> Interface-focused, expects external orchestration",
            "",
            "  Ask user if unclear. State context with rationale.",
            "",
            "INFER architecture (single-turn vs multi-turn):",
            "  SINGLE-TURN when: discrete task, one input -> one output",
            "  MULTI-TURN when: refinement loops, verification, context accumulation",
            "",
            "  NEVER suggest subagents or HITL unless user explicitly requests.",
            "  State architecture choice with rationale.",
            "",
            "IDENTIFY edge cases:",
            "  - What happens with ambiguous input?",
            "  - What errors are expected?",
            "  - What should NOT happen?",
        ],
        routing=LinearRouting(),
        phase="assess",
    ),
    3: Step(
        title="Understand",
        actions=[
            "ARTICULATE semantic understanding of what you're building:",
            "",
            "<purpose>",
            "  What is the high-level goal of this prompt?",
            "  What inputs does it expect?",
            "  What outputs should it produce?",
            "  What does SUCCESS look like?",
            "</purpose>",
            "",
            "<boundaries>",
            "  If this prompt will delegate to sub-agents or components:",
            "  - What is each recipient's bounded responsibility?",
            "  - What is the MINIMUM each recipient needs?",
            "  - What should NOT be passed to recipients? Why?",
            "  If no delegation planned, state: 'No delegation boundaries.'",
            "</boundaries>",
            "",
            "CONTEXT MISMATCH ANTI-PATTERN (review before Design):",
            "",
            "<example type='INCORRECT'>",
            "  Context: SKILL (Claude Code)",
            "  Output: <system>You are a helpful assistant that...</system>",
            "  WHY WRONG: Skills are injected into existing conversation.",
            "             The agent already has identity. Adding <system> is nonsensical.",
            "</example>",
            "<example type='CORRECT'>",
            "  Context: SKILL (Claude Code)",
            "  Output: 'When user requests X, invoke script Y. The script handles Z.'",
            "  WHY RIGHT: Task-focused, no identity, assumes existing agent context.",
            "</example>",
            "",
            "<example type='INCORRECT'>",
            "  Context: SUB-AGENT",
            "  Output: 'You are part of a 6-step workflow. Step 1 does A, step 2...'",
            "  WHY WRONG: Sub-agent needs only its task. Workflow overview is noise.",
            "</example>",
            "<example type='CORRECT'>",
            "  Context: SUB-AGENT",
            "  Output: 'Search for files matching pattern X. Return paths and sizes.'",
            "  WHY RIGHT: Bounded task, minimal context, clear output contract.",
            "</example>",
        ],
        routing=LinearRouting(),
        phase="understand",
    ),
    4: Step(
        title="Design",
        actions=[
            "SELECT applicable techniques for the design:",
            "  Based on requirements, architecture, and EXECUTION CONTEXT from Step 2",
            "",
            "SCAFFOLD based on execution context:",
            "",
            "  IF STANDALONE:",
            "    - Identity/role establishment (<system>You are...)",
            "    - Task description",
            "    - Input handling",
            "    - Output format",
            "    - Constraints and rules",
            "",
            "  IF SKILL (injected into existing agent):",
            "    - Invocation trigger (when to activate)",
            "    - Task instructions (imperative, action-focused)",
            "    - Input/output contract",
            "    - Constraints specific to this skill",
            "    ASSUME: Agent already has identity. Write task-focused instructions only.",
            "",
            "  IF SUB-AGENT (delegated task):",
            "    - Bounded task description",
            "    - Required inputs/outputs",
            "    - Success criteria",
            "    ASSUME: Sub-agent discovers context during execution. Write bounded task only.",
            "",
            "  IF COMPONENT (composable fragment):",
            "    - Interface specification",
            "    - Expected inputs from upstream",
            "    - Outputs for downstream",
            "    ASSUME: External orchestrator provides context. Write interface only.",
            "",
            "For each section, match techniques:",
            "  === SECTION: [name] ===",
            '  Technique: [name] | Trigger: "[quoted]"',
            "  DRAFT: [proposed content]",
            "  RATIONALE: [why this technique here]",
            "",
            "CONTEXT-CORRECTNESS CHECK (before drafting):",
            "",
            "<example context='SKILL' type='INCORRECT'>",
            "  <system>You are a helpful code review assistant...</system>",
            "  WHY WRONG: Skills inject into existing agent. Agent has identity.",
            "</example>",
            "<example context='SKILL' type='CORRECT'>",
            "  When user requests code review, analyze the diff and provide feedback.",
            "  Focus on: correctness, style, potential bugs.",
            "  WHY RIGHT: Task-focused. No identity. Imperative instructions.",
            "</example>",
            "",
            "<example context='SUB-AGENT' type='INCORRECT'>",
            "  You are step 3 of a 6-step workflow. Steps 1-2 have gathered context...",
            "  WHY WRONG: Sub-agent needs only its task. Workflow is orchestrator's concern.",
            "</example>",
            "<example context='SUB-AGENT' type='CORRECT'>",
            "  Search for files matching pattern. Return paths and sizes.",
            "  WHY RIGHT: Bounded task. Clear contract. No workflow knowledge.",
            "</example>",
            "",
            "WRITE complete prompt draft.",
        ],
        routing=LinearRouting(),
        phase="plan",
    ),
    5: STEP_REFINE,
    6: STEP_APPROVE,
    7: Step(
        title="Create",
        actions=[
            "CREATE the prompt file(s).",
            "",
            *integration_check_actions([
                "All requirements addressed?",
                "Edge cases handled?",
                "Structure follows chosen architecture?",
            ]),
            "",
            *anti_pattern_audit_actions("created prompt"),
            "",
            *change_presentation_actions(),
        ],
        routing=TerminalRouting(),
        phase="execute",
    ),
}


PROBLEM_STEPS: dict[int, Step] = {
    1: STEP_TRIAGE,
    2: Step(
        title="Diagnose",
        actions=[
            "UNDERSTAND the problem:",
            "  - What is the observed behavior?",
            "  - What is the expected behavior?",
            "  - When does it occur? (always / sometimes / conditions)",
            "",
            "READ relevant prompt(s) if they exist.",
            "",
            "CLASSIFY the problem:",
            "  PROMPTING: Can be addressed by technique application",
            "  CAPABILITY: Model fundamentally cannot do this",
            "  ARCHITECTURE: Needs structural change, not technique",
            "  EXTERNAL: Problem is in surrounding code, not prompt",
            "",
            "If NOT a prompting issue: state clearly and STOP.",
            "If prompting issue: identify lines that may contribute.",
        ],
        routing=LinearRouting(),
        phase="diagnose",
    ),
    3: Step(
        title="Understand",
        actions=[
            *understand_actions_simple(),
        ],
        routing=LinearRouting(),
        phase="understand",
    ),
    4: Step(
        title="Target Fix",
        actions=[
            "REVERSE LOOKUP - which techniques address this problem class?",
            "  Review Technique Selection Guide for matching triggers",
            "",
            "For each candidate technique:",
            "  - QUOTE trigger condition",
            "  - Explain how problem matches trigger",
            "  - Propose specific change",
            "",
            *change_format_actions("FIX"),
            "  Expected effect: [how this fixes the problem]",
        ],
        routing=LinearRouting(),
        phase="plan",
    ),
    5: STEP_REFINE,
    6: STEP_APPROVE,
    7: Step(
        title="Apply Fix",
        actions=[
            "Apply targeted fix to the prompt.",
            "",
            "VERIFY the fix addresses the stated problem:",
            "  - Does the change match the diagnosed cause?",
            "  - Could it introduce new issues?",
            "",
            *change_presentation_actions(),
        ],
        routing=TerminalRouting(),
        phase="execute",
    ),
}


# =============================================================================
# Workflow Registry
# =============================================================================

WORKFLOWS: dict[str, WorkflowDefinition] = {
    "single-prompt": WorkflowDefinition(
        name="prompt-engineer-single",
        script="skills.prompt_engineer.optimize",
        steps=SINGLE_PROMPT_STEPS,
        description="Optimize a single prompt file",
    ),
    "ecosystem": WorkflowDefinition(
        name="prompt-engineer-ecosystem",
        script="skills.prompt_engineer.optimize",
        steps=ECOSYSTEM_STEPS,
        description="Optimize multiple related prompts",
    ),
    "greenfield": WorkflowDefinition(
        name="prompt-engineer-greenfield",
        script="skills.prompt_engineer.optimize",
        steps=GREENFIELD_STEPS,
        description="Design a new prompt from requirements",
    ),
    "problem": WorkflowDefinition(
        name="prompt-engineer-problem",
        script="skills.prompt_engineer.optimize",
        steps=PROBLEM_STEPS,
        description="Fix a specific issue in existing prompt(s)",
    ),
}

SCOPES = list(WORKFLOWS.keys())


# =============================================================================
# Runtime Functions
# =============================================================================


def get_workflow(scope: str) -> WorkflowDefinition:
    """Get workflow definition for a scope."""
    if scope not in WORKFLOWS:
        sys.exit(f"ERROR: Invalid scope '{scope}'. Valid: {SCOPES}")
    return WORKFLOWS[scope]


def get_step(scope: str, step_num: int) -> Step:
    """Get a specific step from a scope's workflow."""
    workflow = get_workflow(scope)
    if step_num not in workflow.steps:
        valid = sorted(workflow.steps.keys())
        sys.exit(
            f"ERROR: Step {step_num} not in {scope} workflow. Valid: {valid}"
        )
    return workflow.steps[step_num]


def get_total_steps(scope: str) -> int:
    """Get total step count for a scope."""
    return max(get_workflow(scope).steps.keys())


# =============================================================================
# Output Formatting
# =============================================================================


def format_output(step: int, scope: str | None) -> str:
    """Format output for LLM execution."""
    # Step 1 is triage (no scope yet)
    if step == 1:
        step_info = STEP_TRIAGE
        total = 6  # Display as 1/6 since we don't know scope yet
        lines = [
            f"PROMPT ENGINEER - Step {step}/{total}: {step_info.title}",
            "",
            "DO:",
        ]
        for action in step_info.actions:
            lines.append(f"  {action}" if action else "")

        lines.extend([
            "",
            "NEXT: Invoke step 2 with --scope <determined-scope>",
        ])
        return "\n".join(lines)

    # Steps 2+ require scope
    if scope is None:
        sys.exit("ERROR: --scope required for steps 2+. Run step 1 first.")

    step_info = get_step(scope, step)
    total = get_total_steps(scope)

    lines = [
        f"PROMPT ENGINEER - Step {step}/{total}: {step_info.title}",
        f"  Scope: {scope.upper()}",
        "",
    ]

    # Inject READ section at the PLAN step (varies by scope)
    if scope in READ_SPECS:
        read_step, read_refs = READ_SPECS[scope]
        if step == read_step:
            lines.append("READ:")
            for ref in read_refs:
                lines.append(f"  - {ref}")
            lines.append("")

    lines.append("DO:")
    for action in step_info.actions:
        lines.append(f"  {action}" if action else "")

    lines.append("")

    # Next step or completion
    if isinstance(step_info.routing, TerminalRouting):
        lines.append("COMPLETE - Present results to user.")
    else:
        next_step = step + 1
        lines.append(
            f"NEXT: python3 -m skills.prompt_engineer.optimize "
            f"--step {next_step} --scope {scope}"
        )

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Prompt Engineer - Scope-adaptive optimization workflow",
        epilog="Step 1: triage. Steps 2+: scope-specific workflow.",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument(
        "--scope",
        choices=SCOPES,
        default=None,
        help="Required for steps 2+. Run step 1 first to determine scope.",
    )
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")

    # Validate step against scope's workflow
    if args.step > 1:
        if args.scope is None:
            sys.exit(
                "ERROR: --scope required for steps 2+. "
                "Run step 1 first to determine scope."
            )
        total = get_total_steps(args.scope)
        if args.step > total:
            sys.exit(
                f"ERROR: Step {args.step} exceeds total ({total}) "
                f"for scope '{args.scope}'"
            )

    print(format_output(args.step, args.scope))


if __name__ == "__main__":
    main()
