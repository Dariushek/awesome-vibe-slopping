## Validation

- Validation commands live in `.agents/validation.json`, owned by the project. `commit` runs before every commit, `push` before every push.
- Git hooks in `.githooks/` enforce them. Never bypass a hook with `--no-verify`.
- If `core.hooksPath` is unset and `.githooks/` exists, set it with `git config core.hooksPath .githooks`. Never unset it or point it elsewhere.
- `.githooks/validate commit` must pass before reporting work as done, `.githooks/validate all` before a push or pull request. Never report done while a command fails.
- A stage that passed on the same working tree is skipped, so run it freely.
