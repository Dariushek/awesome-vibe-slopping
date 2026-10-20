# awesome-vibe-slopping

Source of truth for coding agent harness across my projects. Provider agnostic first, Claude Code native where it pays off.

## Layout

```
plugins/<bundle>/                 one reusable unit, also a Claude Code plugin
  .claude-plugin/plugin.json      name, version, description
  rules/NN-topic.md               instructions, rendered into AGENTS.md
  skills/<name>/SKILL.md          Agent Skills standard
  agents/<name>.md                subagents
  commands/<name>.md              slash commands
  hooks/hooks.json, .mcp.json     Claude Code only, plugin delivery only
.claude-plugin/marketplace.json   lists every bundle
bin/harness                       sync and validation
```

## Bundles

| Bundle          | Contents                                              |
|-----------------|-------------------------------------------------------|
| `communication` | How agents write and talk. Global, also outside code  |
| `coding`        | General rules for working with code                   |
| `engineering`   | Code quality and testing rules, `commit-message` skill |

## Use in a project

```sh
bin/harness sync ~/Projects/Wealfi coding engineering
bin/harness sync ~/Projects/Wealfi          # later: update from .harness.json
```

Always writes a managed block into the project's `AGENTS.md`. Everything outside the block stays yours. Targets pick the rest:

| Target          | Writes                                                                   | Read by                                   |
|-----------------|--------------------------------------------------------------------------|-------------------------------------------|
| `agents`        | `.agents/skills/`                                                        | Codex, Cursor, Copilot, Gemini and others |
| `claude`        | `@AGENTS.md` in `CLAUDE.md`, copies to `.claude/skills,agents,commands`  | Claude Code                               |
| `claude-plugin` | `@AGENTS.md` in `CLAUDE.md`, enables plugins in `.claude/settings.json`  | Claude Code, auto-updates from GitHub     |

Default `--targets agents,claude`. Use `claude-plugin` instead of `claude` to stop copying and track this repo live.

`.harness.json` records bundles, targets, source commit and a hash per file. Files changed in the project are skipped on resync unless `--force`.

## Global rules

```sh
bin/harness global communication
bin/harness global                  # later: update from saved bundles
```

Writes the managed block into each user-level instructions file whose agent is installed: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`. Bundles are saved in `~/.config/awesome-vibe-slopping/global.json`. Global bundles apply everywhere, so leave them out of project syncs.

Plugin only, without sync:

```
/plugin marketplace add Dariushek/awesome-vibe-slopping
/plugin install engineering@awesome-vibe-slopping
```

## Change something

1. Edit under `plugins/`. New bundle: add its directory and an entry in `marketplace.json`.
2. Bump `version` in the bundle's `plugin.json`.
3. `bin/harness check && claude plugin validate .`
4. Commit, push, resync projects.
