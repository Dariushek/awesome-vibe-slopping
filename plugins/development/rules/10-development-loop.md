## Development loop

Pick the path before writing code:

- Broken behavior: rs-fix-bug.
- A small, clear change with no new business rules: rs-change.
- Anything else: rs-spec, then rs-ui-design if users see the change, then rs-plan. Then run each task with rs-implement-task, or all of them with rs-run-plan.

When a light path hits its stop conditions, switch to rs-spec.

Every finished change gets rs-review. rs-fix-bug, rs-change and rs-run-plan run it themselves; after tasks run by hand, run it after the last one.

Every change leaves a record in `docs/changes/`: what the problem was, what was done and the review.
