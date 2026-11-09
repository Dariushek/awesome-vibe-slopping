---
name: rs-readme
description: Write or update the project README with what it is, its projects, what to install and how to set up, run and test it, with every command verified. Use when the project has no README, when the user asks for one, or when setup or run steps changed.
---

# README

If the project has `.agents/overrides/rs-readme.md`, read it first. Where it conflicts with this skill, it wins.

A new developer on a clean machine follows the README top to bottom and ends with the project running and its tests green.

## Steps

1. **Discover.** Read what defines how the project builds and runs:
   - build and package files, such as solution and project files, package manifests, lock files and toolchain version pins;
   - container files, such as Dockerfiles and compose files;
   - scripts, task runners and Makefiles;
   - configuration examples, such as `.env.example` and settings files, and how secrets are provided;
   - CI workflows, the most reliable source of the real commands;
   - `.agents/validation.json`, ARCHITECTURE.md and the existing README.
2. **Draft.** Write README.md from the template. Keep sections of an existing README that the template does not cover. Mark anything you cannot derive as `???`.
3. **Verify.** Run every command in order, as a newcomer would: setup, run, test. Check the app answers on the documented URLs and ports. Fix the README, never the project, unless the user asks. A command you cannot run, such as one needing cloud credentials, gets marked `Not verified` and goes to the user.
4. **Ask.** Turn every `???` and `Not verified` into a question. Wait for the answers.
5. **Finish.** Remove the markers, show the README and commit it when the user approves.

## Template

````markdown
# Name

One paragraph: what it does and for whom.

## Projects

| Project | Purpose | Kind |
|---------|---------|------|
| src/Api | REST API for orders | web service |
| src/Worker | Sends invoices | background job |

Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## Requirements

| Tool | Version | Install |
|------|---------|---------|
| <runtime or SDK> | <version from the project's pin> | <link or command> |
| <container engine> | <version> | <link or command> |

## Setup

```sh
git clone <url>
cd <name>
cp .env.example .env
<restore dependencies>
<create database, run migrations, seed>
```

Secrets: where they come from and how to set them locally.

## Run

### With containers

```sh
<start command>
```

### Locally

```sh
<run command>
```

| Service | URL |
|---------|-----|
| API | http://localhost:5000 |

Development logins, if any.

## Test

```sh
<test command>
.githooks/validate all
```

## Configuration

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| DATABASE_URL | Database connection | local container | yes |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 5000 in use | Set `PORT` in `.env` |
````

Drop sections that do not apply, such as Projects for a single project or containers when there are none.

## Rules

- Versions come from the project's own pins and files, never from memory.
- Commands are copyable, one per line. Where Windows differs, give both.
- Never put real secrets, tokens or personal data in the README.
- Describe how to run, not how it is built inside. Architecture belongs in ARCHITECTURE.md.
