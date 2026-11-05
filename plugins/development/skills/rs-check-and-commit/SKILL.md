---
name: rs-check-and-commit
description: Run the project's validation gate, fix failures and commit when it passes. Use after finishing a change, before any commit, or when the user asks to check and commit.
---

# Check and commit

## Steps

1. Read the commands under `## Validation` in the project's AGENTS.md. If the section is missing, derive the commands from the project, such as the solution file, package.json scripts or pyproject.toml. Propose them to the user and, once approved, add the section outside any generated block.
2. Check `git status` and the diff. Only the intended change belongs in the commit. Never stage or revert unrelated changes.
3. Review the diff against the project's rules, ADRs and, for UI changes, its design system. Fix what breaks them.
4. Run every command in order. A non-zero exit is a failure.
5. On a failure, make the smallest fix, then re-run the failed command and every command after it. Repeat until all pass.
6. Files changed by a formatter or generator belong to the commit.
7. Commit with the commit-message skill.
8. Report each command with its result and the commit hash.

## Rules

- Never skip a command, swap it for another or report success while one fails.
- If the same failure survives three fixes, or fixing it needs changes outside the current work, stop and report it.
- Never use `--no-verify`, amend or force push.
- Push only when the user asks.
