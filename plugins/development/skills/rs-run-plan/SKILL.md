---
name: rs-run-plan
description: Run all remaining tasks of an approved PLAN.md automatically, in parallel where safe. Use when the user asks to run, execute or automate a plan.
---

# Run plan

If the project has `.agents/overrides/rs-run-plan.md`, read it first. Where it conflicts with this skill, it wins.

## Before starting

1. Read PLAN.md and the spec. Both must be `Approved`.
2. Be on the plan's branch with a clean working tree.
3. Resume safely: reset leftover `in-progress` tasks to `todo`, and remove worktrees and task branches left by an earlier run.

## Loop

1. **Pick.** Ready tasks are `todo` tasks whose dependencies are all `done`. Take up to 3 whose `Files` do not overlap. If you cannot run subagents, take 1 and run it inline with rs-implement-task as usual.
2. **Dispatch.** For each task in the batch:

   ```sh
   base=$(git rev-parse HEAD)
   git worktree add -b "$branch-$id" "../$(basename "$PWD")-$id" "$base"
   ```

   Start the rs-task-implementer agent, or any subagent, in that worktree, on the task's model: `small` is the smallest model you can start subagents on, `default` is your own. Give it the worktree path, the spec path, the plan path and the task ID. Tell it to run rs-implement-task, to leave PLAN.md alone and to report done or blocked with the reason. Install dependencies in the worktree first if the project needs them.
3. **Collect.** For each task that finished, in ID order:

   ```sh
   git cherry-pick "$base..$branch-$id"
   git worktree remove "../$(basename "$PWD")-$id"
   git branch -D "$branch-$id"
   ```

   A cherry-pick conflict means the plan missed a dependency: run `git cherry-pick --abort`, mark the task `blocked` and keep its branch for the user.
4. **Escalate.** A `small` task that reports blocked or leaves a failing gate runs once more on `default`. Reset its worktree first with `git -C "../$(basename "$PWD")-$id" reset --hard "$base"`. Only a `default` run can mark a task `blocked`.
5. **Gate.** After a batch of more than one task, run rs-check-and-commit on the combined result.
6. **Record.** Update the statuses in PLAN.md and commit them, such as `Mark T2 and T3 done`.
7. Repeat until no task is ready.

## Stop and report

- A task is blocked: write the reason under its `Notes`. Never start tasks that depend on it. Other ready tasks may continue.
- A task would contradict an ADR or needs a spec change: stop the whole run.
- The gate cannot pass on the combined result: stop the whole run.

## End

When every task is `done`, run rs-review on the plan branch, then the full gate once more. Check that every scenario, check and non-functional requirement in the spec was verified by its method, and that `test` items have a passing test carrying their ID. Give the user the `manual` items as a checklist with steps. Each one they confirm is recorded; a task moves from `verify` to `done` when all its items are confirmed. Append a `## Run YYYY-MM-DD` section to PLAN.md: each task with its commit and the model that finished it, escalations, blocked tasks with the reason, a verification table with ID, method, result and evidence, the gate result and a link to REVIEW.md. Commit it. Report the same in chat: each task with its commit, the review outcome, any scenario or requirement left unverified, anything blocked with the reason, and the gate result. Ask whether to open a pull request.

## Rules

- Never skip the gate, edit an approved spec or change a task's scope to make progress.
- At most 3 subagents at a time.
- One task stays one commit on the plan's branch.
