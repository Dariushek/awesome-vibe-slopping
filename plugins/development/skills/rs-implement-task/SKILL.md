---
name: rs-implement-task
description: Implement one task from PLAN.md with the development loop. Use when the user names a plan task such as T3, or when rs-run-plan hands one over.
---

# Implement task

If the project has `.agents/overrides/rs-implement-task.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. Read the task, the spec, the ADRs that touch its files and the project's AGENTS.md.
2. Check every task it depends on is `done`. If not, stop and say which.
3. Set its status to `in-progress`.
4. Write each of the task's `test` scenarios as an automated test, with the scenario ID in the test name or display name. Keep its values and steps. Run them and confirm they fail for the expected reason.
5. Implement the smallest change that makes them pass.
6. Verify every scenario, requirement and check of the task with its method from the spec. A task with `Screens` always gets an agent check: run the app as rs-spec describes and walk those screens with the playwright skill at phone and desktop widths, against the prototype. Save evidence to `evidence/<ID>-<name>.png` next to the spec; it goes in the task's commit.
7. Set its status to `done`, or `verify` when only `manual` items are left, with their steps under `Notes`. Run rs-check-and-commit. The PLAN.md update goes in the same commit. Add `Task: T<n>` as the last line of the commit body.
8. Report a verification line per item: ID, method, result, evidence such as a test name, command result or screenshot path.

## When blocked

If the gate cannot pass, the task contradicts an ADR, or the spec is ambiguous: set the status to `blocked`, write the reason under the task's `Notes`, stop and report. Do not guess.

## Rules

- Change only what the task needs. If it needs more, stop and propose a plan change.
- Never edit other tasks.
- When rs-run-plan hands the task over, do not touch PLAN.md at all. Report the outcome instead; the runner updates the plan.
