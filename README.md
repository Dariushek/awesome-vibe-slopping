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
  hooks/hooks.json + scripts      agent hooks, Claude Code only
  .mcp.json                       Claude Code only, plugin delivery only
.claude-plugin/marketplace.json   lists every bundle
bin/harness                       sync and validation
```

## Bundles

| Bundle          | Contents                                              |
|-----------------|-------------------------------------------------------|
| `communication` | How agents write and talk. Global, also outside code  |
| `coding`        | General rules for working with code                   |
| `engineering`   | Code quality and testing rules                        |
| `git`           | `commit-message` skill, enforced by a `commit-msg` hook |
| `csharp`        | C# language rules                                     |
| `browser`       | `playwright` skill                                    |
| `architecture`  | ARCHITECTURE.md, ADRs, architecture tests             |
| `architecture-light` | Short rules in AGENTS.md, no ADRs. Instead of `architecture` |
| `development`   | Bug fix, small change, spec, UI, plan, tasks, review  |
| `validation`    | Build, analysis and test gate enforced by git hooks   |
| `docs`          | `rs-readme`: what to install, how to run and test     |
| `testing`       | Integration tests first, fakes, one e2e per feature. `rs-test-setup` |

## Use in a project

```sh
bin/harness sync ~/Projects/Wealfi coding engineering
bin/harness sync ~/Projects/Wealfi          # later: update from .harness.json
```

Always writes a managed block into the project's `AGENTS.md`. Everything outside the block stays yours. Targets pick the rest:

| Target          | Writes                                                                   | Read by                                   |
|-----------------|--------------------------------------------------------------------------|-------------------------------------------|
| `agents`        | `.agents/skills/`                                                        | Codex, Cursor, Copilot, Gemini and others |
| `claude`        | `@AGENTS.md` in `CLAUDE.md`, copies to `.claude/skills,agents,commands,hooks`, agent hooks in `.claude/settings.json` | Claude Code |
| `claude-plugin` | `@AGENTS.md` in `CLAUDE.md`, enables plugins in `.claude/settings.json`  | Claude Code, auto-updates from GitHub     |

Default `--targets agents,claude`. Use `claude-plugin` instead of `claude` to stop copying and track this repo live.

`.harness.json` records bundles, targets, source commit and a hash per file. Files changed in the project are skipped on resync unless `--force`.

A bundle can name the bundles it needs under `dependencies` in its `plugin.json`. Sync adds them, unless they are installed globally.

```sh
bin/harness sync ~/Projects/Wealfi --dry-run   # show what would change
bin/harness sync --all                         # resync every project synced from this machine
bin/harness status                             # global and every project: outdated, edited, missing
bin/harness remove ~/Projects/Wealfi           # take the harness out again
```

Projects are remembered in `~/.config/awesome-vibe-slopping/projects.json` from their first sync on.

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

`pre-commit` runs `commit`, `pre-push` runs `push`, `.githooks/validate all` runs both. The first failure stops the commit or push. A stage that already passed on the same working tree is skipped, so a gate run right before the commit is not repeated by the hook.

A command can take only the changed files:

```json
{
  "commit": ["eslint {changed:*.ts,*.tsx}", "dotnet format --verify-no-changes --include {changed:*.cs}"]
}
```

`{changed}` is replaced with every changed file, `{changed:<patterns>}` with those matching one of the comma-separated patterns. `commit` compares the working tree with `HEAD`, `push` with the upstream branch, or `origin/HEAD` when there is none. Deleted files are left out, untracked ones included. A command with no matching file is skipped, and a list too long for one command line is split over several runs. Use it for formatters and per-file linters; builds and tests stay whole.

`{python}` is replaced with the interpreter running the hook, so a script runs the same on every system: `{python} .githooks/check-specs {changed:docs/specs/*}`.

### What enforces what

| Check | Enforced by | Can be skipped |
|-------|-------------|----------------|
| Build, analysis, tests | `pre-commit`, `pre-push` | With `--no-verify` |
| Commit message format, no AI attribution | `commit-msg`, from the `git` bundle | With `--no-verify` |
| Spec and plan structure | `.githooks/check-specs`, from the `development` bundle, as a `commit` command | With `--no-verify` |
| `--no-verify`, changes to `core.hooksPath`, `.githooks/` or `.claude/hooks/`, taking the guard out of the agent settings | An agent hook, from the `validation` bundle | By a human, and by agents without tool hooks |
| Subagents kept to their role: the code reviewer to read-only git, the verifier and the gate runner to no git changes, the task implementer to no push | An agent hook, from the `development` bundle | By agents without tool hooks |
| Removing or changing a command in `.agents/validation.json` | The same agent hook, which asks the user | By a human, and by agents without tool hooks |
| All of the above | CI running `.githooks/validate all` | No |

Nothing local is a wall: whoever owns the machine can skip a git hook. The agent hook closes that door for the agent, CI closes it for everyone. A project without CI has defaults, not guarantees.

A minimal CI job, with the project's toolchain set up before the last step:

```yaml
steps:
  - uses: actions/checkout@v7
    with:
      fetch-depth: 0
  - run: python3 .githooks/validate all
```

Git hooks reach a project even when their bundle is installed globally, since a global install cannot deliver them.

An optional `run` entry, `{"start": "...", "url": "..."}`, tells agents how to start the app for checks. Without the file, hooks warn and pass. A fresh clone needs one sync, or `git config core.hooksPath .githooks`.

## Global

```sh
bin/harness global communication browser
bin/harness global                  # later: update from saved bundles
```

Writes the managed block into each user-level instructions file whose agent is installed: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, Devin CLI's `~/.config/devin/AGENTS.md`, `%APPDATA%\devin\AGENTS.md` on Windows, and Devin desktop's `~/.devin/global_rules.md`. Skills are copied to `~/.claude/skills/` and, when Codex or Devin is installed, `~/.agents/skills/`. Agents are copied to `~/.claude/agents/`, the only agent that reads this format. On Windows run `python bin\harness global`. Skills changed outside this repo are skipped unless `--force`.

The list you pass replaces the saved one, and skills of dropped bundles are removed. Bundles and file hashes are saved in `~/.config/awesome-vibe-slopping/global.json`. Global bundles apply everywhere, so leave them out of project syncs; sync warns when rules would apply twice. `bin/harness remove --global` takes it all out.

Plugin only, without sync:

```
/plugin marketplace add Dariushek/awesome-vibe-slopping
/plugin install development@awesome-vibe-slopping
```

A plugin delivers skills, agents, commands and hooks, never rules. Bundles with rules only, such as `engineering`, need a sync.

## Change something

1. Edit under `plugins/`. New bundle: add its directory and an entry in `marketplace.json`.
2. Bump `version` in the bundle's `plugin.json`.
3. `.githooks/validate all`, which runs `bin/harness check`, the tests and `claude plugin validate .`. The commit hook runs it too.
4. Commit, push, `bin/harness sync --all`.
