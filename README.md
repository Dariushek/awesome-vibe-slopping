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
  githooks/<hook>                 git hooks, synced to .githooks/ in every target
  hooks/hooks.json, .mcp.json     Claude Code only, plugin delivery only
.claude-plugin/marketplace.json   lists every bundle
bin/harness                       sync and validation
```

## Bundles

| Bundle          | Contents                                              |
|-----------------|-------------------------------------------------------|
| `communication` | How agents write and talk. Global, also outside code  |
| `coding`        | General rules for working with code                   |
| `engineering`   | Code quality and testing rules                        |
| `git`           | `commit-message` skill                                |
| `csharp`        | C# language rules                                     |
| `browser`       | `playwright` skill                                    |
| `architecture`  | ARCHITECTURE.md, ADRs, architecture tests             |
| `architecture-light` | Short rules in AGENTS.md, no ADRs. Instead of `architecture` |
| `development`   | Bug fix, small change, spec, UI, plan, tasks, review  |
| `validation`    | Build, analysis and test gate enforced by git hooks   |
| `docs`          | `rs-readme`: what to install, how to run and test     |

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

## Project overrides

Every skill first reads `.agents/overrides/<skill>.md` from the project when it exists, and that file wins where it conflicts. Use it for project specifics, such as spec location, commit format or extra steps, without forking the skill. Overrides are project files, never synced or overwritten.

## Validation gate

The `validation` bundle syncs `.githooks/` and sets `core.hooksPath` to it, unless the project already uses another hooks path. The hooks run the commands in `.agents/validation.json`, which the project owns:

```json
{
  "commit": ["dotnet build -warnaserror", "dotnet format --verify-no-changes", "dotnet test"],
  "push": ["dotnet test --filter Category=Slow"]
}
```

`pre-commit` runs `commit`, `pre-push` runs `push`, `.githooks/validate all` runs both. The first failure stops the commit or push. A stage that already passed on the same working tree is skipped, so a gate run right before the commit is not repeated by the hook. An optional `run` entry, `{"start": "...", "url": "..."}`, tells agents how to start the app for checks. Without the file, hooks warn and pass. A fresh clone needs one sync, or `git config core.hooksPath .githooks`.

## Global

```sh
bin/harness global communication browser
bin/harness global                  # later: update from saved bundles
```

Writes the managed block into each user-level instructions file whose agent is installed: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, Devin CLI's `~/.config/devin/AGENTS.md`, `%APPDATA%\devin\AGENTS.md` on Windows, and Devin desktop's `~/.devin/global_rules.md`. Skills are copied to `~/.claude/skills/` and, when Codex or Devin is installed, `~/.agents/skills/`. Agents are copied to `~/.claude/agents/`, the only agent that reads this format. On Windows run `python bin\harness global`. Skills changed outside this repo are skipped unless `--force`.

The list you pass replaces the saved one, and skills of dropped bundles are removed. Bundles and file hashes are saved in `~/.config/awesome-vibe-slopping/global.json`. Global bundles apply everywhere, so leave them out of project syncs.

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
