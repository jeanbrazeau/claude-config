# Source Papers

Academic papers that inform the prompt engineering reference guides. Each
subdirectory maps to a corresponding guide in the parent directory.

## Directory-to-Guide Mapping

| Directory      | Guide                               |
| -------------- | ----------------------------------- |
| `single-turn/` | `prompt-engineering-single-turn.md` |
| `multi-turn/`  | `prompt-engineering-multi-turn.md`  |
| `subagent/`    | `prompt-engineering-subagents.md`   |
| `hitl/`        | `prompt-engineering-hitl.md`        |

## Cross-Cutting Papers

The `agentic/` directory contains papers on reasoning patterns (Tree of
Thoughts, Self-Consistency, Chain-of-Thought variations) that apply across
multiple prompt engineering contexts. These are referenced by multiple guides
rather than mapping to a single one.

## File Naming

Papers follow the pattern: `YYYY-MM-DD Title.pdf`. The date is the paper's
publication or arXiv submission date.

## Adding Papers

When adding new papers:

1. Place in the appropriate category directory
2. Use the standard naming convention
3. Update the corresponding guide if the paper introduces new techniques
