#!/usr/bin/env python3
"""
Plan Executor - Execute approved plans through delegation.

Nine-step workflow:
  1. Execution Planning - analyze plan, build wave list
  2. Reconciliation - validate existing code (conditional)
  3. Implementation - dispatch developers (wave-aware parallel)
  4. Code QR - verify code quality (RULE 0/1/2)
  5. Code QR Gate - route pass/fail
  6. Documentation - TW pass
  7. Doc QR - verify documentation quality
  8. Doc QR Gate - route pass/fail
  9. Retrospective - present summary
"""

import argparse
import sys

from skills.lib.workflow.types import QRState, QRStatus, GateConfig
from skills.lib.workflow.formatters import (
    format_step_output,
    format_gate_step,
    format_subagent_dispatch,
    format_state_banner,
    format_routing,
    format_post_qr_routing,
    format_orchestrator_constraint,
    format_qr_banner,
)
from skills.lib.workflow.cli import add_qr_args
from skills.planner.shared.resources import get_mode_script_path
from skills.lib.beads import is_beads_available


# Module path for -m invocation
MODULE_PATH = "skills.planner.executor"


STEPS = {
    1: {
        "title": "Execution Planning",
        "actions": [
            "Plan file: $PLAN_FILE (substitute from context)",
            "",
            "ANALYZE plan:",
            "  - Count milestones and parse dependency diagram",
            "  - Group milestones into WAVES for execution",
            "  - Set up TodoWrite tracking",
            "",
            "WAVE ANALYSIS:",
            "  Parse the plan's 'Milestone Dependencies' diagram.",
            "  Group into waves: milestones at same depth = one wave.",
            "",
            "  Example diagram:",
            "    M0 (foundation)",
            "     |",
            "     +---> M1 (auth)     \\",
            "     |                    } Wave 2 (parallel)",
            "     +---> M2 (users)    /",
            "     |",
            "     +---> M3 (posts) ----> M4 (feed)",
            "            Wave 3          Wave 4",
            "",
            "  Output format:",
            "    Wave 1: [0]       (foundation, sequential)",
            "    Wave 2: [1, 2]    (parallel)",
            "    Wave 3: [3]       (sequential)",
            "    Wave 4: [4]       (sequential)",
            "",
            "WORKFLOW:",
            "  This step is ANALYSIS ONLY. Do NOT delegate yet.",
            "  Record wave groupings for step 3 (Implementation).",
        ],
        "beads_tracking": True,  # Flag to enable beads issue tracking guidance
    },
    2: {
        "title": "Reconciliation",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/reconciliation.py",
        "mode_total_steps": 4,
        "context_vars": {
            "PLAN_FILE": "path to the plan being executed",
            "N": "milestone number (run once per milestone)",
        },
        "invoke_suffix": " --milestone N",
        "pre_dispatch": [
            "Validate existing code against plan requirements BEFORE executing.",
            "",
            "For EACH milestone, launch quality-reviewer agent:",
        ],
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: SATISFIED | NOT_SATISFIED | PARTIALLY_SATISFIED",
        ],
        "routing": {
            "SATISFIED": "Mark milestone complete, skip execution",
            "NOT_SATISFIED": "Execute milestone normally",
            "PARTIALLY_SATISFIED": "Execute only missing parts",
        },
        "extra_instructions": [
            "",
            "Parallel execution: May run reconciliation for multiple milestones",
            "in parallel (multiple Task calls in single response) when milestones",
            "are independent.",
        ],
    },
    3: {
        "title": "Implementation",
        # Handled specially in format_output - has normal and fix modes
        "beads_tracking": True,  # Flag to enable beads milestone tracking guidance
    },
    4: {
        "title": "Code QR",
        "is_qr": True,
        "qr_name": "CODE QR",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/post-impl-code.py",
        "mode_total_steps": 5,
        "context_vars": {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from all milestones",
        },
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES (XML grouped by milestone).",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "developer"},
    },
    # Step 5 is the Code QR gate - handled separately
    6: {
        "title": "Documentation",
        # Handled specially in format_output - has normal and fix modes
    },
    7: {
        "title": "Doc QR",
        "is_qr": True,
        "qr_name": "DOC QR",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/post-impl-doc.py",
        "mode_total_steps": 4,
        "context_vars": {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
        },
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES.",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "technical-writer"},
    },
    # Step 8 is the Doc QR gate - handled separately
    9: {
        "title": "Retrospective",
        "actions": [
            "PRESENT retrospective to user (do not write to file):",
            "",
            "EXECUTION RETROSPECTIVE",
            "=======================",
            "Plan: [path]",
            "Status: COMPLETED | BLOCKED | ABORTED",
            "",
            "Milestone Outcomes: | Milestone | Status | Notes |",
            "Reconciliation Summary: [if run]",
            "Plan Accuracy Issues: [if any]",
            "Deviations from Plan: [if any]",
            "Quality Review Summary: [counts by category]",
            "Feedback for Future Plans: [actionable suggestions]",
        ],
        "beads_close": True,  # Flag to close parent feature issue if all milestones done
    },
}


# Gate configuration for step 5 (Code QR Gate)
CODE_QR_GATE = GateConfig(
    qr_name="Code QR",
    work_step=3,
    pass_step=6,
    pass_message="Code quality verified. Proceed to documentation.",
    self_fix=False,
    fix_target="developer",
)

# Gate configuration for step 8 (Doc QR Gate)
DOC_QR_GATE = GateConfig(
    qr_name="Doc QR",
    work_step=6,
    pass_step=9,
    pass_message="Documentation verified. Proceed to retrospective.",
    self_fix=False,
    fix_target="technical-writer",
)


def format_step_3_implementation(qr: QRState, total_steps: int, milestone_count: int) -> str:
    """Format step 3 implementation output."""

    if qr.failed:
        # Fix mode - dispatch developer with QR findings using structured dispatch
        banner = format_state_banner("IMPLEMENTATION FIX", qr.iteration, "fix")
        dispatch_block = format_subagent_dispatch(
            agent="developer",
            context_vars={
                "PLAN_FILE": "path to the executed plan",
                "MODIFIED_FILES": "actual file paths from milestones",
            },
            invoke_cmd="",  # free_form mode, no script
            free_form=True,
            qr_fix_mode=True,
        )
        actions = [banner, ""]
        actions.extend([
            "FIX MODE: Code QR found issues.",
            "",
            format_orchestrator_constraint(),
            "",
            dispatch_block,
            "",
            "Developer reads QR report and fixes issues in <milestone> blocks.",
            "After developer completes, re-run Code QR for fresh verification.",
        ])
        return format_step_output(
            script="executor",
            step=3,
            total=total_steps,
            title="Implementation - Fix Mode",
            actions=actions,
            next_command=f"python3 -m {MODULE_PATH} --step 4 --total-steps {total_steps}",
            is_step_one=False,
        )
    else:
        # Normal mode - dispatch developers for all milestones
        actions = [
            "Execute ALL milestones using wave-aware parallel dispatch.",
            "",
            "WAVE-AWARE EXECUTION:",
            "  - Milestones within same wave: dispatch in PARALLEL",
            "    (Multiple Task calls in single response)",
            "  - Waves execute SEQUENTIALLY",
            "    (Wait for wave N to complete before starting wave N+1)",
            "",
            "Use waves identified in step 1.",
            "",
        ]

        # Add beads tracking guidance if enabled and available
        if info.get("beads_tracking") and is_beads_available():
            actions.extend([
                "OPTIONAL BEADS TRACKING:",
                "  Before starting each wave:",
                "    bd update [MILESTONE-ID] --status in_progress",
                "  After milestone completes:",
                "    bd close [MILESTONE-ID] \"Milestone N complete\"",
                "",
            ])

        actions.extend([
            format_orchestrator_constraint(),
            "",
            "FOR EACH WAVE:",
            "  1. Dispatch developer agents for ALL milestones in wave:",
            "     Task(developer): Milestone N",
            "     Task(developer): Milestone M  (if parallel)",
            "",
            "  2. Each prompt must include:",
            "     - Plan file: $PLAN_FILE",
            "     - Milestone: [number and name]",
            "     - Files: [exact paths to create/modify]",
            "     - Acceptance criteria: [from plan]",
            "",
            "  3. Wait for ALL agents in wave to complete",
            "",
            "  4. Run tests: pytest / tsc / go test -race",
            "     Pass criteria: 100% tests pass, zero warnings",
            "",
            "  5. Proceed to next wave (repeat 1-4)",
            "",
            "After ALL waves complete, proceed to Code QR.",
            "",
            "ERROR HANDLING (you NEVER fix code yourself):",
            "  Clear problem + solution: Task(developer) immediately",
            "  Difficult/unclear problem: Task(debugger) to diagnose first",
            "  Uncertain how to proceed: AskUserQuestion with options",
        ]
        return format_step_output(
            script="executor",
            step=3,
            total=total_steps,
            title="Implementation",
            actions=actions,
            next_command=f"python3 -m {MODULE_PATH} --step 4 --total-steps {total_steps}",
            is_step_one=False,
        )


def format_step_6_documentation(qr: QRState, total_steps: int) -> str:
    """Format step 6 documentation output."""
    mode_script = get_mode_script_path("tw/post-impl.py")

    if qr.failed:
        # Fix mode - dispatch TW with Doc QR findings using structured dispatch
        banner = format_state_banner("DOCUMENTATION FIX", qr.iteration, "fix")
        invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps 6 --qr-fail --qr-iteration {qr.iteration}"
        dispatch_block = format_subagent_dispatch(
            agent="technical-writer",
            context_vars={
                "PLAN_FILE": "path to the executed plan",
                "MODIFIED_FILES": "actual file paths from milestones",
            },
            invoke_cmd=invoke_cmd,
            free_form=False,
            qr_fix_mode=True,
        )
        actions = [banner, ""]
        actions.extend([
            "FIX MODE: Doc QR found issues.",
            "",
            format_orchestrator_constraint(),
            "",
            dispatch_block,
            "",
            "TW reads QR report and fixes documentation issues.",
            "After TW completes, re-run Doc QR for fresh verification.",
        ])
        return format_step_output(
            script="executor",
            step=6,
            total=total_steps,
            title="Documentation - Fix Mode",
            actions=actions,
            next_command=f"python3 -m {MODULE_PATH} --step 7 --total-steps {total_steps}",
            is_step_one=False,
        )
    else:
        # Normal mode - dispatch TW
        dispatch_block = format_subagent_dispatch(
            agent="technical-writer",
            context_vars={
                "PLAN_FILE": "path to the executed plan",
                "MODIFIED_FILES": "actual file paths from milestones",
            },
            invoke_cmd=f"python3 -m {mode_script} --step 1 --total-steps 6",
        )
        actions = [
            format_orchestrator_constraint(),
            "",
            dispatch_block,
            "",
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: Documentation report format",
            "",
            "Skip if ALL milestones were documentation-only.",
        ]
        return format_step_output(
            script="executor",
            step=6,
            total=total_steps,
            title="Documentation",
            actions=actions,
            next_command=f"python3 -m {MODULE_PATH} --step 7 --total-steps {total_steps}",
            is_step_one=False,
        )


def format_output(step: int, total_steps: int,
                  qr_iteration: int, qr_fail: bool, qr_status: str,
                  reconciliation_check: bool, milestone_count: int) -> str:
    """Format output for display using XML format."""

    # Construct QRState from legacy parameters
    status = QRStatus(qr_status) if qr_status else None
    qr = QRState(iteration=qr_iteration, failed=qr_fail, status=status)

    # Step 5 is the Code QR gate
    if step == 5:
        if not qr_status:
            return "Error: --qr-status required for step 5"
        return format_gate_step(
            script="executor",
            step=5,
            total=total_steps,
            gate=CODE_QR_GATE,
            qr=qr,
            cmd_template=f"python3 -m {MODULE_PATH}",
        )

    # Step 8 is the Doc QR gate
    if step == 8:
        if not qr_status:
            return "Error: --qr-status required for step 8"
        return format_gate_step(
            script="executor",
            step=8,
            total=total_steps,
            gate=DOC_QR_GATE,
            qr=qr,
            cmd_template=f"python3 -m {MODULE_PATH}",
        )

    # Step 3 has special handling (implementation with fix mode)
    if step == 3:
        return format_step_3_implementation(qr, total_steps, milestone_count)

    # Step 6 has special handling (documentation with fix mode)
    if step == 6:
        return format_step_6_documentation(qr, total_steps)

    info = STEPS.get(step, STEPS[9])

    # Handle QR step in fix mode (developer/TW fixes, not QR re-run)
    if info.get("is_qr") and qr.failed:
        post_qr_config = info.get("post_qr_routing", {})
        fix_target = post_qr_config.get("fix_target", "developer")
        qr_name = info.get("qr_name", "QR")

        banner = format_state_banner(qr_name, qr.iteration, "fix")
        dispatch_block = format_subagent_dispatch(
            agent=fix_target,
            context_vars={
                "PLAN_FILE": "path to the executed plan",
                "MODIFIED_FILES": "actual file paths from milestones",
            },
            invoke_cmd="",
            free_form=True,
            qr_fix_mode=True,
        )
        fix_actions = [banner, ""] + [
            f"FIX MODE: {qr_name} found issues.",
            "",
            format_orchestrator_constraint(),
            "",
            dispatch_block,
            "",
            f"{fix_target.title()} reads QR report and fixes issues.",
            f"After {fix_target} completes, re-run {qr_name} for fresh verification.",
        ]
        # Return flat next command - re-run this step for fresh QR
        return format_step_output(
            script="executor",
            step=step,
            total=total_steps,
            title=f"{info['title']} - Fix Mode",
            actions=fix_actions,
            next_command=f"python3 -m {MODULE_PATH} --step {step} --total-steps {total_steps}",
            is_step_one=False,
        )

    is_complete = step >= total_steps

    # Build actions
    actions = []

    # Add QR banner for QR steps using XML format
    if info.get("is_qr"):
        qr_name = info.get("qr_name", "QR")
        actions.append(format_qr_banner(qr_name, qr))
        actions.append("")

    # Handle dispatch steps with new structure
    if info.get("is_dispatch"):
        # Add pre-dispatch instructions
        pre_dispatch = info.get("pre_dispatch", [])
        actions.extend(pre_dispatch)

        # Add orchestrator constraint before dispatch
        actions.append(format_orchestrator_constraint())
        actions.append("")

        # Generate dispatch block
        mode_script = get_mode_script_path(info["mode_script"])
        mode_total_steps = info.get("mode_total_steps", 5)
        dispatch_agent = info.get("dispatch_agent", "agent")
        context_vars = info.get("context_vars", {})
        invoke_suffix = info.get("invoke_suffix", "")

        dispatch_block = format_subagent_dispatch(
            agent=dispatch_agent,
            context_vars=context_vars,
            invoke_cmd=f"python3 -m {mode_script} --step 1 --total-steps {mode_total_steps}{invoke_suffix}",
        )
        actions.append(dispatch_block)
        actions.append("")

        # Add post-dispatch instructions
        post_dispatch = info.get("post_dispatch", [])
        actions.extend(post_dispatch)

        # Add post-QR routing block for QR steps
        post_qr_config = info.get("post_qr_routing")
        if post_qr_config:
            routing_block = format_post_qr_routing(
                self_fix=post_qr_config.get("self_fix", False),
                fix_target=post_qr_config.get("fix_target", "developer"),
            )
            actions.append(routing_block)

        # Add routing block if present
        routing = info.get("routing")
        if routing:
            actions.append("")
            actions.append(format_routing(routing))

        # Add extra instructions if present
        extra_instructions = info.get("extra_instructions", [])
        actions.extend(extra_instructions)
    elif "actions" in info:
        # Non-dispatch step with explicit actions
        actions.extend(info["actions"])

    # Add beads integration guidance for step 1 when available
    if info.get("beads_tracking") and is_beads_available():
        actions.extend([
            "",
            "═══════════════════════════════════════════════════════════",
            "OPTIONAL: BEADS ISSUE TRACKING",
            "═══════════════════════════════════════════════════════════",
            "",
            "Beads (bd) is available. Check for existing issues related to this plan:",
            "",
            "1. Search for feature issue:",
            "   bd list --status open | grep \"[feature name]\"",
            "",
            "2. If feature issue exists with milestone issues:",
            "   - Note milestone issue IDs for status tracking",
            "   - You'll update their status during execution",
            "",
            "3. If no issues exist:",
            "   - Issues may have been created during planning",
            "   - Or this execution doesn't use issue tracking",
            "   - Either is fine - tracking is optional",
            "",
            "During execution (step 3), you'll optionally update milestone status:",
            "  - bd update [MILESTONE-ID] --status in_progress  # When starting",
            "  - bd close [MILESTONE-ID] \"Milestone complete\"  # When done",
            "═══════════════════════════════════════════════════════════",
        ])

    # Add beads close guidance for step 9 retrospective when available
    if info.get("beads_close") and is_beads_available():
        actions.extend([
            "",
            "═══════════════════════════════════════════════════════════",
            "OPTIONAL: CLOSE BEADS FEATURE ISSUE",
            "═══════════════════════════════════════════════════════════",
            "",
            "If you tracked this feature with beads and ALL milestones are complete:",
            "",
            "Close the parent feature issue:",
            "  bd close [FEATURE-ID] \"Feature complete - all milestones done\"",
            "",
            "Check remaining work:",
            "  bd ready  # See what's next",
            "═══════════════════════════════════════════════════════════",
        ])

    # Build next command(s)
    next_command = None
    if_pass = None
    if_fail = None

    if is_complete:
        # Final step - no invoke_after, just present retrospective
        actions.append("")
        actions.append("EXECUTION COMPLETE - Present retrospective to user.")
    elif step == 1:
        # Step 1 has special guidance embedded in actions
        actions.extend([
            "",
            "=" * 70,
            "MANDATORY NEXT ACTION",
            "=" * 70,
        ])
        if reconciliation_check:
            next_command = f"python3 -m {MODULE_PATH} --step 2 --total-steps {total_steps} --reconciliation-check"
        else:
            actions.extend([
                "Proceed to Implementation step.",
                "Use the wave groupings from your analysis.",
                "=" * 70,
            ])
            next_command = f"python3 -m {MODULE_PATH} --step 3 --total-steps {total_steps}"
    elif step == 4:
        # Code QR step uses branching
        if_pass = f"python3 -m {MODULE_PATH} --step 5 --total-steps {total_steps} --qr-status pass"
        if_fail = f"python3 -m {MODULE_PATH} --step 5 --total-steps {total_steps} --qr-status fail"
    elif step == 7:
        # Doc QR step uses branching
        if_pass = f"python3 -m {MODULE_PATH} --step 8 --total-steps {total_steps} --qr-status pass"
        if_fail = f"python3 -m {MODULE_PATH} --step 8 --total-steps {total_steps} --qr-status fail"
    else:
        next_command = f"python3 -m {MODULE_PATH} --step {step + 1} --total-steps {total_steps}"

    return format_step_output(
        script="executor",
        step=step,
        total=total_steps,
        title=info["title"],
        actions=actions,
        next_command=next_command,
        if_pass=if_pass,
        if_fail=if_fail,
        is_step_one=(step == 1),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Plan Executor - Execute approved plans",
        epilog="Steps: plan -> reconcile -> implement -> code QR -> gate -> docs -> doc QR -> gate -> retrospective",
    )

    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    add_qr_args(parser)
    parser.add_argument("--reconciliation-check", action="store_true")
    parser.add_argument("--milestone-count", type=int, default=0)

    args = parser.parse_args()

    if args.step < 1 or args.step > 9:
        sys.exit("Error: step must be 1-9")

    if args.step == 5 and not args.qr_status:
        sys.exit("Error: --qr-status required for step 5")

    if args.step == 8 and not args.qr_status:
        sys.exit("Error: --qr-status required for step 8")

    print(format_output(args.step, args.total_steps,
                        args.qr_iteration, args.qr_fail, args.qr_status,
                        args.reconciliation_check, args.milestone_count))


if __name__ == "__main__":
    main()
