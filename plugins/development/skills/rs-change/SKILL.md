---
name: rs-change
description: Implement a small, clear change without a spec, such as a simple user story or a technical change with no new business logic. Use when the user asks for a small feature, a refactor, a dependency update or a configuration change.
---

# Change

If the project has `.agents/overrides/rs-change.md`, read it first. Where it conflicts with this skill, it wins.

## Steps

1. **Context.** Read the project's AGENTS.md, the ADRs and the code the change touches.
2. **Contract.** In chat, not in a file:
   - For a user story: 1 to 3 scenarios in Given/When/Then with concrete values.
   - For a technical change: what must stay the same and how that is proven, such as the existing tests or a build.

   Wait for the user's OK.
3. **Implement.** Scenarios become failing tests first, then the code that makes them pass. For a technical change, the tests are green before and after.
4. **UI.** If a UI changed, check it with the playwright skill.
5. **Record.** Write `docs/changes/YYYY-MM-DD-<slug>.md` from the template below.
6. **Commit.** Run rs-check-and-commit. The record goes in the same commit.
7. **Review.** Run rs-review.

## Change record template

```markdown
# Title

- Date: YYYY-MM-DD
- Kind: bug | change | spec

## Problem

What was wrong or what was needed, and who noticed.

## Cause

Bugs only: the root cause, with file and line.

## Contract

The scenarios or the "stays the same" list agreed in chat, each with its test name.

## Done

What changed and why this way.

## Review

Filled by rs-review.
```

For `Kind: spec`, Problem is one line and the rest is a link to the spec folder.

## Stop and propose rs-spec when

- The change brings new domain concepts, states or business rules.
- More than one question is open after the contract.
- It needs an architecture decision.
- It grows past one commit.
