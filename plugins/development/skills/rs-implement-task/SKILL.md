---
name: rs-implement-task
description: Implement one task from PLAN.md with the development loop. Use when the user names a plan task such as T3, or when rs-run-plan hands one over.
---

# Implement task

## Steps

1. Read the task, the spec, the ADRs that touch its files and the project's AGENTS.md.
2. Check every task it depends on is `done`. If not, stop and say which.
3. Set its status to `in-progress`.
4. Write each of the task's scenarios as an automated test, with the scenario ID in the test name or display name. Keep its values and steps. Run them and confirm they fail for the expected reason.
5. Implement the smallest change that makes it pass.
6. If a UI changed, check it in a browser with the playwright skill and compare it with the task's prototype screens.
7. Confirm every scenario test of the task passes, and verify each of its non-functional requirements the way the spec says.
8. Set its status to `done` and run rs-check-and-commit. The PLAN.md update goes in the same commit. Add `Task: T<n>` as the last line of the commit body.

## When blocked

If the gate cannot pass, the task contradicts an ADR, or the spec is ambiguous: set the status to `blocked`, write the reason under the task's `Notes`, stop and report. Do not guess.

## Rules

- Change only what the task needs. If it needs more, stop and propose a plan change.
- Never edit other tasks.
- When rs-run-plan hands the task over, do not touch PLAN.md at all. Report the outcome instead; the runner updates the plan.
