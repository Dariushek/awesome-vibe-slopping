---
name: rs-spec
description: Write a feature specification before implementation. Use when the user asks for a spec, or before a change that touches 3 or more files or needs an architecture decision.
---

# Specification

## Steps

1. **Context.** Read the project's AGENTS.md, the ADRs and the code the change touches. Stop reading once you can name the areas and contracts involved.
2. **Unknowns.** List the critical unknowns: answers that, guessed wrong, would force rewriting the spec. Always include the split check: if the request bundles capabilities that would each work alone, ask whether to split it into separate specs.
3. **Skeleton.** Write `docs/specs/YYYY-MM-DD-<slug>/SPEC.md` with only Problem, Outcome and Out of scope, plus an `Open questions` block right after the title: `Q1`, `Q2`, one per line, short, yes/no or multiple choice where possible. Follow the project's existing spec location and format if it has one.
4. **Stop.** Show the skeleton and wait until the user answers every question. Never answer them yourself.
5. **Fill.** Apply the answers, remove the answered questions and write the rest of the template. If new unknowns come up, stop again for those only.
6. **Review.** Hand the spec path, and nothing else, to a fresh subagent with the checklist below. If you cannot run subagents, apply the checklist yourself, line by line. Fix every finding.
7. **Approve.** Show the spec and the review result. Iterate until the user approves, then set `Status: Approved`.
8. **Decisions.** Record each architecture decision with rs-architecture-decision. Decisions the user approved with the spec are `Accepted`. Link the ADRs from the spec.
9. Next step: rs-plan.

## Template

```markdown
# Title

- Date: YYYY-MM-DD
- Status: Draft | Approved

## Open questions

- Q1: ...

## Problem

Who has it and why it matters.

## Outcome

What is true when this is done.

## Out of scope

## Acceptance criteria

1. AC1: one testable statement.

## Design

Approach, affected areas, data and API changes.

## Failure scenarios

What can fail and what the user sees when it does.

## Architecture decisions

Each decision, with a link to its ADR once written.
```

## Review checklist

- **One capability.** Parts that would each work alone belong in separate specs.
- **Testable.** Every acceptance criterion can be checked by a test. "Fast" fails; "list loads under 500 ms with 10k rows" passes.
- **Failure modes.** Every external call, migration and long-running job has a failure scenario with user-visible behavior.
- **Reversible.** Every state change has a way back.
- **Existing building blocks.** The design reuses what the project already has, or says why not.
- **Contracts.** Every changed public API, event, schema or config is named, with a migration path when breaking.
- **ADRs.** Nothing contradicts an accepted ADR without proposing a new one.
- **No noise.** Standard boilerplate is not described.

## Rules

- Skeleton first, always. The open questions gate is a hard stop.
- Never start implementation from a Draft spec, and never edit code while writing one.
