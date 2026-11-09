---
name: rs-review
description: Review a finished change with a fresh agent for correctness, security, rule breaches and spec coverage, then fix the clear findings. Use at the end of rs-run-plan, after the last task done by hand, after rs-fix-bug or rs-change, or when the user asks for a code review.
---

# Review

If the project has `.agents/overrides/rs-review.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. **Base.** Find the commit the change started from: the plan branch's fork point, `git merge-base HEAD <main branch>`, or the commit before a single change. Ask if unclear.
2. **Review.** Hand the base and the spec or task path, nothing else, to the rs-code-reviewer agent, or any fresh subagent with its instructions. If you cannot run subagents, review the diff yourself against the same list.
3. **Verify.** Check each finding against the code. Drop false positives with the reason.
4. **Triage.**
   - Fix automatically: a `certain` bug or security hole with a concrete failure case, a missing scenario test, a test that proves nothing, a rule or ADR breach with an obvious fix.
   - Ask the user: anything that changes behavior beyond the spec, needs a design or security policy choice, contradicts an ADR, or is `uncertain`.
5. **Fix.** One finding per commit. Write a failing test first where behavior is wrong, then fix, then rs-check-and-commit.
6. **Re-review.** Run step 2 once more, on the fix commits only. Fix what it confirms. Never run a third round; report what is left.
7. **Report.** Each finding with its outcome: fixed with commit, dropped with reason, or waiting for the user.
   - When the change has a spec, append a section per round to `REVIEW.md` next to `SPEC.md`. If `docs/changes/` has no record for the spec yet, add one with `Kind: spec` from the rs-change template.
   - When it has a change record in `docs/changes/`, fill its `## Review` section, one subsection per round.
   - Otherwise report in chat only.

   Commit the report with the commit-message skill.

## Report template

```markdown
## Review YYYY-MM-DD, round 1

- Base: <commit>
- Head: <commit>

| # | Severity | Category | Where | Finding | Outcome |
|---|----------|----------|-------|---------|---------|
| 1 | high | security | src/orders.ts:42 | Order id from the URL is not checked against the user | fixed in a1b2c3d |
| 2 | medium | correctness | src/price.ts:10 | ... | dropped: total is rounded earlier in sum() |
| 3 | medium | spec | - | S4 has no test | waiting for the user |
```

## Rules

- Never fix a finding you could not verify.
- Never weaken a test, a validation or a security check to make a finding go away.
- `critical` and `high` security findings are always reported, also when fixed.
