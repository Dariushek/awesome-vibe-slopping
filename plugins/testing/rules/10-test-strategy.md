## Test strategy

- Before writing tests, read the `## Testing` section of the project's AGENTS.md, outside the generated block. If it is missing, suggest rs-test-setup to the user.
- Test behavior through the public API: the web API when there is one, otherwise the public API of the module.
- The default test is an integration test: the API with its database.
- Database, when the project uses containers: the real engine in a container with in-memory storage.
- Database, when it does not: the in-memory provider of the ORM, or a hand-written fake behind the repository interface when the app uses plain SQL. Never add containers for the tests alone.
- Fake only what cannot run locally, such as message queues and cloud services. Fake at the boundary, with one fake per service shared by all tests.
- Test internals directly only when the public API cannot reach the case or makes the test awkward. Say why in the test.
- Every test owns its data. Tests pass alone, in any order and in parallel.
- Tests read as documentation of the system. Setup goes through `Given` helpers that call the public API, never through the database.
- Every feature has one end-to-end test of its main path, from the UI to the database, against the app running locally. The plan for a feature names the task that writes it.
- The end-to-end suite starts the app itself, with a fresh database and the same fakes.
- No UI component tests, unless a component holds logic the end-to-end test cannot cover.
