---
name: rs-spec
description: Write a feature specification by interviewing the user about the domain, resulting in workflows and test scenarios in natural but precise language. Use when the user asks for a spec, or before a change that touches 3 or more files or needs an architecture decision.
---

# Specification

The spec describes the domain the way the user sees it, then the scenarios that prove the feature works. Scenarios become automated tests, one or more per scenario.

## Steps

1. **Context.** Read the project's AGENTS.md, the ADRs, existing specs and the code the change touches. Stop reading once you can name the areas involved.
2. **Skeleton.** Write `docs/specs/YYYY-MM-DD-<slug>/SPEC.md` with Problem, Outcome, Out of scope and the first round of questions. Always include the split check: if the request bundles capabilities that would each work alone, ask whether to split it into separate specs. Follow the project's existing spec location and format if it has one.
3. **Interview.** Ask in rounds of at most five questions, numbered `Q1`, `Q2` and onward. Stop after each round and wait for the answers. Never answer them yourself. Walk the workflow step by step, using the techniques below, until nothing is `???`. Then run a round on non-functional requirements.
4. **Model.** Write Glossary, Data, Life cycle and Workflows from the answers, in the notation below. Show it to the user and correct it with them.
5. **Scenarios and requirements.** Derive scenarios from the workflows and constraints, and write the non-functional requirements. Show them to the user.
6. **Design.** Add the technical part: approach, affected areas, failures, architecture decisions.
7. **Review.** Hand the spec path, and nothing else, to a fresh subagent with the checklist below. If you cannot run subagents, apply the checklist yourself, line by line. Fix every finding.
8. **Approve.** Iterate until the user approves, then set `Status: Approved`.
9. **Decisions.** Record each architecture decision with rs-architecture-decision. Decisions the user approved with the spec are `Accepted`. Link the ADRs from the spec.
10. Next step: rs-ui-design when users see the change, otherwise rs-plan with `Prototype: Not applicable`.

## Interview techniques

- **Walk the flow.** "What happens first?" "Then what?" "What happens when that fails?" One workflow at a time.
- **Use their words.** Every term the user uses goes to the Glossary. Never introduce technical words such as float, table or null. Ask "what do you call that?" instead.
- **Dig at "it depends".** Ask "depends on what?" It usually hides a choice between kinds of things.
- **Pin down every value.** What makes it valid? Unit, format, smallest and largest allowed.
- **Find the stages.** "How do you tell one that is done from one that is not?" Each answer is a life cycle state.
- **Find the outcomes.** Every way a workflow can end, including the bad ones.
- **Find dependencies.** What outside the feature does each step need, and what happens when it is unavailable?
- **Follow the money.** Ask what matters most to the business. Priorities shape the design.
- Mark anything unknown as `???` and turn it into a question.

## Non-functional questions

Ask only what applies to the feature, and push every answer to a number or a checkable statement. "Fast" is not an answer; "under 1 s for 95% of requests" is.

- **Volume and speed.** How many, how often, how fast must it respond, what peak?
- **Availability.** What happens to the business when it is down? What may be lost?
- **Access.** Who may do what, and who must never see what?
- **Data.** What is personal or sensitive, how long is it kept, what must be deleted?
- **Audit.** Who changed what and when, does anyone need to know?
- **Reach.** Which devices, browsers, languages and accessibility needs?
- **Operations.** What must be logged or alerted on?

## Template

````markdown
# Title

- Date: YYYY-MM-DD
- Status: Draft | Approved
- Prototype: path, set by rs-ui-design | Not applicable

## Open questions

- Q1: ...

## Problem

Who has it and why it matters.

## Outcome

What is true when this is done.

## Out of scope

## Glossary

- Order quantity: how much of a product the customer orders.

## Data

```
data OrderLine =
  ProductCode
  AND OrderQuantity

data ProductCode = WidgetCode OR GizmoCode
data WidgetCode = "W" followed by 4 digits
data UnitQuantity = whole number from 1 to 1000
data CustomerInfo = ???
```

## Life cycle

```
UnvalidatedOrder -> ValidatedOrder -> PricedOrder
```

What each stage adds and what is forbidden before it, such as: an order is not shipped before it is priced.

## Workflows

```
workflow "Place order" =
  triggered by: order form received
  input: order form
  needs: product catalog, address checking service
  output: OrderPlaced OR InvalidOrder
  side effects: acknowledgment sent to the customer

  1. validate the order
     if any part is invalid: put it on the invalid orders pile, stop
  2. price each line, sum the amount to bill
  3. send the acknowledgment
  4. return OrderPlaced
```

## Scenarios

### S1. Valid widget order is placed

Given widget W1234 costs 10.00 in the catalog
When a customer orders 3 of W1234
Then the order is placed with amount to bill 30.00
And the customer receives an acknowledgment

### S2. Too many units are rejected

Given widget W1234 is in the catalog
When a customer orders 1001 of W1234
Then the order goes to the invalid orders pile
And the reason is that the quantity is above 1000

## Non-functional requirements

- N1: Placing an order responds within 1 s for 95% of requests at 50 orders per minute. Verified by: load test.
- N2: Only staff with the pricing role can change a price. Verified by: scenario S7.
- N3: Customer addresses are deleted 2 years after the last order. Verified by: test of the cleanup job.

## Design

Approach, affected areas, data and API changes.

## Failures

Technical failures, such as an unavailable dependency, and what the user sees.

## Architecture decisions

Each decision, with a link to its ADR once written.
````

## Writing scenarios

- One scenario per path through each workflow: the main path and every branch that ends differently.
- Boundary scenarios for every constraint: the smallest and largest allowed values, and one step past each.
- One scenario per life cycle rule, such as an unpriced order cannot be shipped.
- Concrete values, never "some quantity". Glossary terms only.
- Each scenario checks one behavior and has a title that states it.

## Review checklist

- **One capability.** Parts that would each work alone belong in separate specs.
- **Nothing unknown.** No `???` and no unanswered question left. `Not applicable` counts as answered.
- **Domain stays domain.** Glossary, Data, Life cycle, Workflows and Scenarios contain no technical terms.
- **Every path covered.** Each workflow branch and outcome has a scenario.
- **Every constraint covered.** Each bound has boundary scenarios.
- **Scenarios testable.** Concrete values, one behavior each, an observable result.
- **Non-functional asked and measurable.** Each applicable question was asked, each requirement has a number or checkable statement and says how it is verified.
- **Failures.** Every dependency and long-running step has a failure with user-visible behavior.
- **Reversible.** Every state change has a way back.
- **Existing building blocks.** The design reuses what the project already has, or says why not.
- **Contracts.** Every changed public API, event, schema or config is named, with a migration path when breaking.
- **ADRs.** Nothing contradicts an accepted ADR without proposing a new one.

## Rules

- Questions first, always. Each round is a hard stop.
- The user may answer that a question, topic or section does not apply. Skip it, never ask it again, and write `Not applicable` under its heading instead of removing it, so a reviewer sees it was considered.
- Never start implementation from a Draft spec, and never edit code while writing one.
