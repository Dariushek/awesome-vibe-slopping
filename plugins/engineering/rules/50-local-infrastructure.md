## Local infrastructure

- When the app needs a database or another service to run locally and the project uses containers, start it from a `compose.yaml` at the project root.
- Without containers, the project's AGENTS.md names how each service is provided. Never add container files on your own.
- The file lists only what the app depends on. The app itself runs from its toolchain.
- Pin every image tag. Use the tag the tests use for the same service.
- Bind each port to `127.0.0.1`, on a fixed host port that is no default of the service, so projects do not collide.
- Keep data in a named volume, so it survives a restart.
- Give each service a health check, so `up --wait` returns when the service is usable.
- Use credentials that exist nowhere else. They are committed, so they protect nothing.
- The app reads its connection settings from local configuration that is never deployed, such as a secret store or an untracked env file.
- Tests start their own containers and never use these services. The app's data and test data stay apart.
