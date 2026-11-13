---
name: rs-plan
description: Split an approved specification into small, well-described tasks in PLAN.md. Use after a spec is approved, or when the user asks for an implementation plan.
---

# Plan

If the project has `.agents/overrides/rs-plan.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. Read the spec. If its status is not `Approved`, or its `Prototype:` line is empty, stop and say so.
2. Split the work into tasks. Write `PLAN.md` next to `SPEC.md` from the template.
3. Show it to the user. Iterate until they approve. Then set `Status: Approved`. Run `.githooks/check-specs <spec folder>` and fix what it reports.
4. Create the branch named in the plan from the current branch. Commit the whole spec folder to it, `prototype/` included, with everything rs-spec and rs-ui-design wrote outside it, such as ADRs and changes to ARCHITECTURE.md or AGENTS.md. The working tree must end clean; rs-run-plan needs that.
5. Tell the user the two ways on: `rs-implement-task T1` and onward by hand, or `rs-run-plan` for all of it.

## Template

```markdown
# Plan: Title

- Spec: [SPEC.md](SPEC.md)
- Branch: feat/<slug>
- Status: Draft | Approved

## Tasks

| ID | Title | Depends on | Status |
|----|-------|------------|--------|
| T1 | ...   | -          | todo   |

## T1. Title

- Goal: one or two sentences.
- Files: paths created or changed.
- Screens: prototype screens it builds, if any.
- Scenarios: which spec scenarios it makes pass, such as S1, S2.
- Requirements: which non-functional requirements it satisfies, such as N1.
- Checks: which spec checks it satisfies, such as C1.
- Model: small | default
- Notes: anything the implementer must know.
```

Status is one of `todo`, `in-progress`, `verify`, `done`, `blocked`. `verify` means the code is committed and only manual checks are left; it counts as done for dependencies.

## After a spec change

When an approved spec was changed with rs-spec, set the plan to `Draft` and bring it in line:

- Rewrite `todo` and `blocked` tasks the change touches.
- Never rewrite a `done` or `verify` task. Add a new task for what must change in its code.
- Add tasks for new scenarios, drop tasks whose scenarios are gone.

Show the changes, get approval, set `Approved` and commit spec and plan together.

## Rules

- One task is one commit, small enough to review in a few minutes.
- Each task is self-contained. An agent with no chat history must be able to do it from the task and the spec alone.
- Every scenario in the spec is covered by exactly one task. Every non-functional requirement and check is covered by at least one task.
- A task depends on another when it needs that task's code or touches the same files. Tasks with no dependency between them and no shared files can run in parallel, so split along those lines where it is natural.
- List every file a task touches. rs-run-plan uses `Files` to decide what runs in parallel.
- `Model: small` for mechanical work that follows an existing pattern, such as data types, wiring, CRUD, configuration or a UI like existing screens. `Model: default` for logic, concurrency, security, anything spanning several areas, or when unsure.
