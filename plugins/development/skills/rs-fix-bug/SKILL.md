---
name: rs-fix-bug
description: Fix a bug by reproducing it with a failing test, finding the root cause and making the smallest fix. Use when the user reports broken behavior, an error, a crash or a regression.
---

# Fix bug

If the project has `.agents/overrides/rs-fix-bug.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. **Understand.** Restate the bug in one sentence: what happens, what should happen, where. Ask if the expected behavior is unclear.
2. **Reproduce.** Write a failing automated test that shows the bug. For a UI bug that cannot be tested directly, reproduce it with the playwright skill first, then capture it in a test. If it does not reproduce, stop and report what you tried.
3. **Root cause.** Read the code without editing it. Name the cause, not the symptom, and the line where it starts.
4. **Fix.** Make the smallest change that removes the cause. The test turns green and no other test turns red.
5. **Siblings.** Check whether the same cause breaks anything else nearby. Report findings, fix only with the user's OK.
6. **Record.** Write `docs/changes/YYYY-MM-DD-<slug>.md` from the rs-change template, with `Kind: bug` and the Cause filled.
7. **Commit.** Run rs-check-and-commit. The record goes in the same commit.
8. **Review.** Run rs-review.

## Stop and propose rs-spec when

- The expected behavior is a business decision nobody has made.
- The fix changes the domain model, a public contract or an architecture decision.

## Rules

- Never fix a symptom only, such as a null check that hides the cause.
- Never change a test to match the bug.
