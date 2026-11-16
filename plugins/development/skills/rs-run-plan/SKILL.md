---
name: rs-run-plan
description: Run all remaining tasks of an approved PLAN.md automatically, in parallel where safe, or every approved plan one after another. Use when the user asks to run, execute or automate a plan or all plans.
---

# Run plan

If the project has `.agents/overrides/rs-run-plan.md`, read it first. Where it conflicts with this skill, it wins.

Runs one plan. When the user asks for all plans, follow `## All plans`, which runs the rest of this skill once per plan.

## Before starting

1. Read PLAN.md and the spec. Both must be `Approved`.
2. Be on the plan's branch with a clean working tree.
3. Resume safely. An earlier run may have stopped after a task was finished but before it was collected. For each task branch it left, check the last commit: when its body ends with `Task: <ID>` and the task is not `done`, collect it first:

   ```sh
   git cherry-pick "$(git merge-base HEAD "$branch-$id")..$branch-$id"
   ```

   Record it as the loop would. Then reset leftover `in-progress` tasks to `todo`, remove the worktrees and the task branch of every task that is not `blocked`.
4. Add `.worktrees/` to `.git/info/exclude` if it is not there. Worktrees live inside the repository, so sandboxed agents can write to them.

## Loop

1. **Pick.** Ready tasks are `todo` tasks whose dependencies are all `done`. Take up to 3 whose `Files` do not overlap. At most one task in a batch may run the app or use another shared resource, such as a fixed port or a local database: any task with `Screens` or an `agent check`. If the project's tests share such a resource, take 1. If you cannot run subagents, take 1 and run it inline with rs-implement-task as usual.
2. **Dispatch.** For each task in the batch:

   ```sh
   base=$(git rev-parse HEAD)
   git worktree add -b "$branch-$id" ".worktrees/$id" "$base"
   ```

   Start the rs-task-implementer agent, or any subagent, in that worktree, on the task's model: `small` is the smallest model you can start subagents on, `default` is your own. Give it the worktree path, the spec path, the plan path and the task ID. Tell it to run rs-implement-task, to leave PLAN.md alone and to report done or blocked with the reason. Install dependencies in the worktree first if the project needs them.
3. **Collect.** For each task that finished, in ID order:

   ```sh
   git cherry-pick "$base..$branch-$id"
   git worktree remove --force ".worktrees/$id"
   git branch -D "$branch-$id"
   ```

   A cherry-pick conflict means the plan missed a dependency: run `git cherry-pick --abort`, mark the task `blocked`, remove its worktree and keep its branch for the user.
4. **Escalate.** A `small` task that reports blocked or leaves a failing gate runs once more on `default`. Reset its worktree first with `git -C ".worktrees/$id" reset --hard "$base"`. Only a `default` run can mark a task `blocked`; then remove its worktree and keep its branch.
5. **Gate.** After a batch of more than one task, run rs-check-and-commit on the combined result.
6. **Record.** Update the statuses in PLAN.md and commit them, such as `Mark T2 and T3 done`.
7. Repeat until no task is ready.

## Stop and report

- A task is blocked: write the reason under its `Notes`. Never start tasks that depend on it. Other ready tasks may continue.
- A task would contradict an ADR or needs a spec change: stop the whole run. Propose the change; rs-spec describes how to change an approved spec, rs-plan how to update the plan after.
- The gate cannot pass on the combined result: stop the whole run.

## End

When every task is `done`, run rs-review on the plan branch, then rs-verify on the spec, then the full gate once more. Check that every scenario, check and non-functional requirement in the spec was verified by its method, and that `test` items have a passing test carrying their ID. Give the user the `manual` items as a checklist with steps. Each one they confirm is recorded; a task moves from `verify` to `done` when all its items are confirmed. Append a `## Run YYYY-MM-DD` section to PLAN.md: each task with its commit and the model that finished it, escalations, blocked tasks with the reason, a verification table with ID, method, result and evidence, the gate result and a link to REVIEW.md. Commit it. Report the same in chat: each task with its commit, the review outcome, any scenario or requirement left unverified, anything blocked with the reason, and the gate result. Ask whether to open a pull request.

## All plans

Runs every approved plan that has work left, one after another. Never two at once: they share the working tree, the ports and the database.

1. **Find.** Start with a clean working tree and note the current branch. A plan lives on its own branch, so list each branch with the plan that names it:

   ```sh
   git for-each-ref --format='%(refname:short)' refs/heads | while read -r branch; do
       git ls-tree -r --name-only "$branch" | grep '/PLAN\.md$' | while read -r plan; do
           git show "$branch:$plan" | grep -qxF -- "- Branch: $branch" && echo "$branch $plan"
       done
   done
   ```

   Keep the plans that are `Approved` and have a `todo` or `in-progress` task.
2. **Order.** Take the order the user gave. Otherwise sort by spec folder name, oldest first. Note the tip of every branch in the queue with `git rev-parse`, then show the queue and start. Do not wait for an answer.
3. **Run.** For each plan, check out its branch. It builds on an earlier plan of the queue when that plan's noted tip is an ancestor: `git merge-base --is-ancestor <noted tip> HEAD`. Bring in the work of each such plan, in queue order, with `git merge --no-edit <its branch>`. Then run the plan from `## Before starting` through `## End`, with two changes: collect the `manual` items instead of waiting for the user, and do not ask about a pull request.
4. **Skip.** A plan finished clean when every task is `done` or `verify`, review and verification left no open finding and the gate passes. Skip a plan that builds on one that did not finish clean, and a plan whose merge conflicts, after `git merge --abort`. Where `## Stop and report` stops the whole run, it stops that plan only. The other plans still run.
5. **Report.** Check out the branch noted in step 1. Report every plan with its branch and outcome, the skipped ones with the reason. Give the `manual` items as one checklist grouped by plan. Then ask which pull requests to open. The pull request of a plan that builds on another shows that plan's commits too, until it is merged.

## Rules

- Never skip the gate, edit an approved spec or change a task's scope to make progress.
- At most 3 subagents at a time.
- One task stays one commit on the plan's branch.
