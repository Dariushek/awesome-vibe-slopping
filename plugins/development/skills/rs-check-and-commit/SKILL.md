---
name: rs-check-and-commit
description: Run the project's validation gate, fix failures and commit when it passes. Use after finishing a change, before any commit, or when the user asks to check and commit.
---

# Check and commit

If the project has `.agents/overrides/rs-check-and-commit.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. Read the `commit` commands in `.agents/validation.json`. If the file is missing, derive the commands from the project, such as the solution file, package.json scripts or pyproject.toml. Propose them to the user and, once approved, write the file:

   ```json
   {
     "commit": ["<build>", "<static analysis>", "<tests>", "{python} .githooks/check-specs {changed:docs/specs/*}"],
     "push": ["<slow tests>"],
     "run": {"start": "<start the app>", "url": "<where it answers>"}
   }
   ```

   `push` commands run before a push, or when the caller asks for the full gate. `run` serves agent checks; leave it out when there is no app to start.

2. Check `git status` and the diff. Only the intended change belongs in the commit. Never stage or revert unrelated changes.
3. Review the diff against the project's rules, ADRs and, for UI changes, its design system. Fix what breaks them.
4. Run the gate. With `.githooks/validate`, run `.githooks/validate commit`, or `.githooks/validate all` for the full gate. It remembers the tree that passed, so the commit hook does not run the commands again. Without it, run every command in order. A non-zero exit is a failure. If the rs-gate-runner agent is available, let it run the gate, so only failures reach you.
5. On a failure, make the smallest fix, then re-run the gate. Repeat until it passes.
6. Files changed by a formatter or generator belong to the commit.
7. Commit with the commit-message skill.
8. Report each command with its result and the commit hash.

## Rules

- Never skip a command, swap it for another or report success while one fails.
- If the same failure survives three fixes, or fixing it needs changes outside the current work, stop and report it.
- Never amend or force push.
- Push only when the user asks.
