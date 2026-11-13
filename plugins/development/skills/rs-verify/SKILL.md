---
name: rs-verify
description: Verify a finished feature against its specification with a fresh agent that uses the running app and never reads the implementation, then fix what fails. Use at the end of rs-run-plan, after the last task of a plan done by hand, or when the user asks whether a feature does what its spec says.
---

# Verify

If the project has `.agents/overrides/rs-verify.md`, read it first. Where it conflicts with this skill, it wins.

rs-review reads the code. This skill uses the product. The verifier knows the spec and what the app does, never what the code intends.

## Steps

1. **Verify.** Hand the spec path, and nothing else, to the rs-verifier agent, or any fresh subagent told to apply the verification checklist below. If you cannot run subagents, apply it yourself.
2. **Record.** Append the results as returned to `REVIEW.md` next to `SPEC.md`, in a section from the template, and commit it with the evidence, before fixing anything. A session that stops now loses nothing.
3. **Fix.** Each `fail` is a bug: fix it with rs-fix-bug, one per commit. If the spec is wrong instead, stop and propose the change; rs-spec describes how to change an approved spec.
4. **Verify again.** Run steps 1 and 2 once more, on the failed items only. Never run a third round; report what is left.
5. **Report.** Set the result of each fixed item in the recorded section, such as `fail, fixed in a1b2c3d`. Commit it with the commit-message skill. Give the user the `manual` items as a checklist with steps.

## Verification checklist

The verifier never edits files, apart from saving evidence.

1. Read the spec, the files it links, such as the prototype, and the `run` entry in `.agents/validation.json`. Never read the implementation or the diff.
2. Start the app with `run.start` and wait until `run.url` answers. Stop it when done.
3. Verify every scenario, check and non-functional requirement:
   - **On screen.** Walk the Given, When and Then with the playwright skill, with the scenario's own values, at phone and desktop widths. Compare against the prototype. Do this for every scenario a user sees, whatever its method.
   - **No screen.** Run it through the public API of the running app, when it has one.
   - **`test`.** Find the test carrying the ID. Read it to confirm it checks what the item says, with its values. Run it.
   - **`command`.** Run the command and compare with the expected result.
   - **`manual`.** Do not verify. List it with its steps.
4. Try one step past each scenario: the input just outside a bound, the action repeated, the step out of order. Report anything the spec does not cover as `gap`, not as `fail`.
5. Save evidence to `evidence/verify-<ID>-<name>.png` next to the spec, or the command output for items without a screen.
6. Report each item with: ID, method, `pass`, `fail`, `gap` or `not verified`, and the evidence. A `fail` gives the steps, the expected and the observed result. A `not verified` gives the reason.

## Report template

```markdown
## Verification YYYY-MM-DD, round 1

| ID | Method | Result | Evidence |
|----|--------|--------|----------|
| S1 | on screen | pass | evidence/verify-S1-order-placed.png |
| S2 | on screen | fail, fixed in a1b2c3d | Expected rejection above 1000 units, order was placed |
| S3 | manual | waiting for the user | - |
| N1 | command | not verified | No load test tool installed |
```

## Rules

- Never mark an item `pass` without evidence.
- Never weaken a scenario, a test or the spec to make an item pass.
- A `gap` goes to the user as a question, never straight into the code.
