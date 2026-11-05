## Development loop

- A change that touches 3 or more files or needs an architecture decision starts with rs-spec, then rs-ui-design if users see the change, then rs-plan. Then run each task with rs-implement-task, or all of them with rs-run-plan.
- A smaller change goes straight to code: a failing test first, then the implementation, then rs-check-and-commit.
