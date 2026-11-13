# Working on this repo

This repo is the harness source of truth. Layout and usage: README.md.

- Write for any agent. No vendor names in rules unless the rule is vendor-specific.
- Rules: one topic per file, start with a `##` heading, numeric prefix sets order.
- Skills: `skills/<name>/SKILL.md` with `name` equal to the directory and a `description` saying when to use it. Right after the title, point to the project override `.agents/overrides/<name>.md`.
- Agents: `agents/<name>.md` with `name` equal to the file stem and a `description`.
- Nothing project-specific here. Project facts stay in the project's own AGENTS.md, outside the managed block.
- Bump the bundle `version` on every change.
- `bin/harness check` fails when a changed bundle has no version bump, a referenced skill does not exist or descriptions drift.
- Change `bin/harness` with a test in `tests/`.
- `bin/harness` is Python standard library only.

<!-- harness:begin generated from awesome-vibe-slopping, edit there -->
## Validation

- Validation commands live in `.agents/validation.json`, owned by the project. `commit` runs before every commit, `push` before every push.
- Git hooks in `.githooks/` enforce them. Never bypass a hook with `--no-verify`.
- If `core.hooksPath` is unset and `.githooks/` exists, set it with `git config core.hooksPath .githooks`. Never unset it or point it elsewhere.
- `.githooks/validate commit` must pass before reporting work as done, `.githooks/validate all` before a push or pull request. Never report done while a command fails.
- A stage that passed on the same working tree is skipped, so run it freely.
- A command can take only the changed files: `{changed}` or `{changed:*.cs,*.ts}` in it is replaced with them, and the command is skipped when there are none. Use it for formatters and per-file linters, never for builds, tests or analysis that spans files.
<!-- harness:end -->
