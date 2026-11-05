## Validation

- Validation commands live in `.agents/validation.json`, owned by the project. `commit` runs before every commit, `push` before every push.
- Git hooks in `.githooks/` enforce them. Never bypass a hook with `--no-verify`, and never change `core.hooksPath`.
- Run `.githooks/validate all` before reporting work as done. Never report done while a command fails.
