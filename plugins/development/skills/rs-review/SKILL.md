---
name: rs-review
description: Review a finished change with a fresh agent for correctness, security, rule breaches and spec coverage, then fix the clear findings. Use at the end of rs-run-plan, after the last task done by hand, after rs-fix-bug or rs-change, or when the user asks for a code review.
---

# Review

If the project has `.agents/overrides/rs-review.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. **Base.** Find the commit the change started from: the plan branch's fork point, `git merge-base HEAD <main branch>`, or the commit before a single change. Ask if unclear.
2. **Review.** Hand the base and the spec or task path, nothing else, to the rs-code-reviewer agent, or any fresh subagent told to apply the review checklist below. If you cannot run subagents, apply it yourself.
3. **Record.** Write the findings as returned, each with outcome `open`, and commit them with the commit-message skill, before doing anything about them. A session that stops now loses nothing.
   - When the change has a spec, append a section per round to `REVIEW.md` next to `SPEC.md`. If `docs/changes/` has no record for the spec yet, add one with `Kind: spec` from the rs-change template.
   - When it has a change record in `docs/changes/`, fill its `## Review` section, one subsection per round.
   - Otherwise keep them in chat only.
4. **Verify.** Check each finding against the code. Drop false positives with the reason.
5. **Triage.**
   - Fix automatically: a `certain` bug or security hole with a concrete failure case, a missing scenario test, a test that proves nothing, a rule or ADR breach with an obvious fix.
   - Ask the user: anything that changes behavior beyond the spec, needs a design or security policy choice, contradicts an ADR, or is `uncertain`.
6. **Fix.** One finding per commit. Write a failing test first where behavior is wrong, then fix, then rs-check-and-commit.
7. **Re-review.** Run steps 2 and 3 once more, on the fix commits only. Fix what it confirms. Never run a third round; report what is left.
8. **Report.** Set the outcome of each recorded finding: fixed with commit, dropped with reason, or waiting for the user. No finding stays `open`. Commit the report with the commit-message skill and give the same in chat.

## Review checklist

The reviewer never edits files.

1. Read `git diff <base>..HEAD`, the project's AGENTS.md, ARCHITECTURE.md, the accepted ADRs touching the changed files and the spec or task if given.
2. Read enough of the surrounding code to judge each change in context.
3. Look for:
   - **Correctness.** Wrong logic, unhandled failures, missing edge cases, races, resource leaks.
   - **Security.** Injection, missing authentication or authorization checks, secrets in code or logs, sensitive data exposed in output or errors, unsafe deserialization, path traversal, weak crypto, unvalidated input crossing a trust boundary, new dependencies with known vulnerabilities.
   - **Rules.** Breaches of the project's rules and accepted ADRs.
   - **Spec.** Every scenario, check and requirement is verified by its method. Each `test` item has a test carrying its ID that checks what it says. Access and data rules are verified.
   - **Tests.** Tests that pass without proving the behavior.
4. Report each finding with: severity `critical`, `high`, `medium` or `low`; category; file and line; the problem; a concrete input or state that fails; the fix; `certain` or `uncertain`.

No style findings; formatters and analyzers cover those. Report nothing you cannot tie to a concrete failure case.

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
