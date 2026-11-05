---
name: rs-plan
description: Split an approved specification into small, well-described tasks in PLAN.md. Use after a spec is approved, or when the user asks for an implementation plan.
---

# Plan

If the project has `.agents/overrides/rs-plan.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. Read the spec. If its status is not `Approved`, or its `Prototype:` line is empty, stop and say so.
2. Split the work into tasks. Write `PLAN.md` next to `SPEC.md` from the template.
3. Show it to the user. Iterate until they approve. Then set `Status: Approved`.
4. Create the branch named in the plan from the current branch and commit `SPEC.md` and `PLAN.md` to it.
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
- Notes: anything the implementer must know.
```

Status is one of `todo`, `in-progress`, `done`, `blocked`.

## Rules

- One task is one commit, small enough to review in a few minutes.
- Each task is self-contained. An agent with no chat history must be able to do it from the task and the spec alone.
- Every scenario in the spec is covered by exactly one task. Every non-functional requirement is covered by at least one task.
- A task depends on another when it needs that task's code or touches the same files. Tasks with no dependency between them and no shared files can run in parallel, so split along those lines where it is natural.
- List every file a task touches. rs-run-plan uses `Files` to decide what runs in parallel.
