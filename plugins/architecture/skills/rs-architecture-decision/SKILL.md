---
name: rs-architecture-decision
description: Record an architecture decision as an ADR in the project. Use when the user asks for an ADR, when an architecture decision is made during work, or when a feature specification contains architecture decisions.
---

# Architecture decision record

If the project has `.agents/overrides/rs-architecture-decision.md`, read it first. Where it conflicts with this skill, it wins.

One ADR per decision. Write it when the decision is made, not after the code.

## What counts

A decision is architectural when it is hard to reverse or shapes code beyond one feature: structure and layers, module boundaries, dependencies and frameworks, data storage and schema strategy, integration protocols, cross-cutting patterns such as auth, error handling or messaging.

Naming, local refactors and choices inside one class are not ADRs.

## From a specification

Read the spec and list every architecture decision in it. Show the list to the user before writing. Each confirmed decision becomes its own ADR that links the spec.

## Where

1. Use the project's existing ADR directory, such as `docs/adr/`, `doc/adr/` or `docs/decisions/`.
2. If none exists, create `docs/adr/`.

File name: `NNNN-kebab-case-title.md`, next free number, zero padded to four digits.

If existing ADRs use another format or naming, follow theirs instead of the template below.

## Template

```markdown
# NNNN. Title in imperative form

- Date: YYYY-MM-DD
- Status: Proposed | Accepted | Superseded by [NNNN](NNNN-title.md)
- Spec: link, if any
- Enforced by: the automated check, or `review only` with the reason

## Context

The forces at play: problem, constraints, requirements. Facts, not opinions.

## Decision

What we do, stated actively: "We use ...".

## Alternatives

Each option considered and why it lost.

## Consequences

What becomes easier, what becomes harder, what follow-up work it creates.
```

## Rules

- Status is `Accepted` only when the user decided or confirmed. A decision you inferred is `Proposed`; ask the user to confirm.
- Never rewrite an accepted ADR. To change a decision, write a new ADR and set the old one's status to `Superseded by`.
- Keep it short. One screen is the target.
- If the directory has an index such as `README.md`, add the new ADR to it.
- When an ADR becomes `Accepted` and the project has ARCHITECTURE.md, update the sections it changes and link the ADR. A superseded ADR's links move to the new one.
- A rule that code can check gets an automated check in the validation gate, written with the user's OK.
