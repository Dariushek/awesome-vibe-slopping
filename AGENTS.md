# Working on this repo

This repo is the harness source of truth. Layout and usage: README.md.

- Write for any agent. No vendor names in rules unless the rule is vendor-specific.
- Rules: one topic per file, start with a `##` heading, numeric prefix sets order.
- Skills: `skills/<name>/SKILL.md` with `name` equal to the directory and a `description` saying when to use it.
- Agents: `agents/<name>.md` with `name` equal to the file stem and a `description`.
- Nothing project-specific here. Project facts stay in the project's own AGENTS.md, outside the managed block.
- Bump the bundle `version` on every change.
- Run `bin/harness check` and `claude plugin validate .` before committing.
- `bin/harness` is Python standard library only.
