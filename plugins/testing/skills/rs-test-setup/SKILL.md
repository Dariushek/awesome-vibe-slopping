---
name: rs-test-setup
description: Set up automated testing in a project: integration tests through the public API with a database, fakes for services that cannot run locally, one end-to-end test and the commands in the validation gate. Use when the project has no `## Testing` section in AGENTS.md, when the user asks to set up or change how the project is tested, or when a new kind of infrastructure needs a fake.
---

# Test setup

If the project has `.agents/overrides/rs-test-setup.md`, read it first. Where it conflicts with this skill, it wins.

The result: a fixture every test builds on, one passing test per kind and a `## Testing` section in AGENTS.md that tells the next agent how to add a test.

## Steps

1. **Context.** Read AGENTS.md, `.agents/validation.json`, the existing tests and what defines the stack:
   - the public API: web endpoints, or the public surface of each module;
   - the database engine and how the app connects to it;
   - container files, and whether a container engine is available;
   - every external service the app calls, such as queues, storage, mail and third-party APIs;
   - the UI, if any, and how the app starts.
2. **Decide.** Apply the test strategy rules:
   - entry point: the web API, or the module API when there is no host;
   - database: the real engine in a container with in-memory storage, an in-memory provider, a hand-written fake;
   - fakes: one per external service that cannot run locally;
   - end-to-end: the browser test tool of the stack, and how the suite starts the app.
3. **Ask.** One round of at most five questions, numbered `Q1` and onward, on what the code does not answer. Stop and wait for the answers.
4. **Scaffold.** If `stacks/` next to this skill has a recipe for the stack, follow it. Otherwise build the same parts with the tools of the stack:
   - a fixture that starts the app in-process against a fresh database and exposes a client;
   - `Given` helpers that set state through the public API;
   - the fakes, registered in place of the real clients, with a way to read what the app sent;
   - one integration test of existing behavior;
   - an end-to-end suite that starts the app itself, with one test of a main path.
5. **Verify.** Run each suite twice and in parallel. Break the behavior under test once and confirm the test fails. Report the run times.
6. **Wire.** Put the commands in `.agents/validation.json`: integration tests under `commit`, end-to-end tests under `push`. Update the test section of the README.
7. **Record.** Write a `## Testing` section in AGENTS.md from the template, outside any generated block. Show it and iterate until the user approves. Then commit.

## Template

```markdown
## Testing

- Integration tests: `tests/Api.Tests`, through the web API. Run: `<command>`.
- Database: PostgreSQL in a container, one database per test.
- Fakes: `FakeMailSender`, `FakeBlobStorage` in `tests/Api.Tests/Fakes`.
- Fixture: `ApiFixture`. Set state with its `Given` helpers, never through the database.
- End-to-end tests: `tests/E2E`, one per feature. Run: `<command>`.
- Unit tests: only `src/Pricing/Rounding`, unreachable through the API.
```

## Rules

- Never change production behavior to make it testable. Adding a seam, such as an interface at an external boundary, is fine.
- The suites need nothing started by hand. A container already running may speed them up, never be required.
- A fake holds state in memory and behaves like the service for the cases the app uses. No mocking library for a service that has a fake.
- Isolation by database or by unique data, never by cleaning up after a test.
- Changing the entry point, the database tier or a fake needs the user's OK.
