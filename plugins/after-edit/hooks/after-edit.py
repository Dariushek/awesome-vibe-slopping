#!/usr/bin/env python3
"""Run the project's commands on files the agent changed, such as formatters.

Usage: after-edit [edit|finish], with the hook call as JSON on standard input,
from Claude Code or Devin.

Commands come from .agents/after-edit.json:

    {"edit": ["..."], "finish": ["..."]}

A plain list is the `edit` list. `edit` runs after each file edit, on that
file. `finish` runs in order when the agent finishes its turn, on every file
changed since HEAD, and not again until the tree changes.

`{changed}` becomes the files, `{changed:*.cs,*.ts}` those matching a pattern,
and a command whose placeholder matches nothing is skipped. A second colon joins
the files into one argument: `--include={changed:*.cs:;}` gives `--include=a.cs;b.cs`.
`{python}` is this interpreter.

A failing `edit` command never blocks: its output goes back to the agent as
context. A failing `finish` command sends the agent back to fix it, once per tree.
"""

import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG = Path(".agents") / "after-edit.json"
EDIT, FINISH = "edit", "finish"
STAGES = (EDIT, FINISH)
PATH_FIELDS = ("file_path", "notebook_path", "path", "target_file", "filename", "file")
# A patch names its files in headers, such as `*** Update File: src/a.cs`.
PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Move to): (.+?)\s*$", re.MULTILINE)
PROJECT_DIRS = ("CLAUDE_PROJECT_DIR", "DEVIN_PROJECT_DIR")
CHANGED = re.compile(r"\{changed(?::([^}:]*))?(?::([^}]+))?\}")
CMD_VARIABLE = re.compile(r"%[^%]+%")
PYTHON = "{python}"
TIMEOUT = {EDIT: 60, FINISH: 600}
OUTPUT_LIMIT = 2000
STAMP_FILE = "harness-after-edit.json"


def quote(names, windows=os.name == "nt"):
    """Shell arguments. cmd.exe takes `&` and friends literally only inside double quotes."""
    if windows:
        return " ".join(f'"{name}"' for name in names)

    return shlex.join(names)


def matching(files, patterns):
    if not patterns:
        return files

    return [f for f in files if any(fnmatch.fnmatch(f, p.strip()) for p in patterns.split(","))]


def expand(command, files):
    """The command for these files, None when a placeholder matches none of them."""
    if any(not matching(files, patterns) for patterns, _ in CHANGED.findall(command)):
        return None

    def fill(match):
        found = matching(files, match.group(1))
        separator = match.group(2)
        return quote([separator.join(found)]) if separator else quote(found)

    return CHANGED.sub(fill, command.replace(PYTHON, quote([sys.executable])))


def git(root, *args, env=None):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=env)


def project_root(call):
    start = next((os.environ[v] for v in PROJECT_DIRS if os.environ.get(v)), None) or call.get("cwd") or os.getcwd()
    result = git(start, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip() if result.returncode == 0 else start).resolve()


def load_config(root):
    """Commands per stage."""
    try:
        config = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except OSError:
        return {}
    except ValueError as error:
        raise SystemExit(f"after-edit: {CONFIG}: invalid JSON: {error}") from error

    config = {EDIT: config} if isinstance(config, list) else config
    if not isinstance(config, dict):
        raise SystemExit(f"after-edit: {CONFIG} must be a list or an object of lists")

    unknown = sorted(set(config) - set(STAGES))
    if unknown:
        raise SystemExit(f"after-edit: {CONFIG}: unknown keys {', '.join(unknown)}, use {' and '.join(STAGES)}")

    for stage in STAGES:
        listed = config.get(stage, [])
        if not isinstance(listed, list) or not all(isinstance(c, str) for c in listed):
            raise SystemExit(f"after-edit: {CONFIG}: {stage} must be a list of command strings")

    return config


def named_files(tool_input):
    names = [str(tool_input[f]) for f in PATH_FIELDS if tool_input.get(f)]
    for value in tool_input.values():
        if isinstance(value, str):
            names += PATCH_FILE.findall(value)

    return names


def inside(root, names):
    """Existing files among the names, relative to the root, posix style."""
    found = []
    for name in names:
        path = (root / name).resolve()
        if not path.is_file() or (CMD_VARIABLE.search(name) and os.name == "nt"):
            continue

        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue

        if relative not in found:
            found.append(relative)

    return found


def edited_files(call, root):
    tool_input = call.get("tool_input")
    return inside(root, named_files(tool_input if isinstance(tool_input, dict) else {}))


def file_list(root, *args):
    result = subprocess.run(["git", *args, "-z"], cwd=root, capture_output=True)
    if result.returncode != 0:
        return None

    return [n for n in result.stdout.decode("utf-8", "surrogateescape").split("\0") if n]


def changed_files(root):
    """Files that differ from HEAD, untracked ones included and deleted ones left out."""
    untracked = file_list(root, "ls-files", "--others", "--exclude-standard") or []
    tracked = file_list(root, "diff", "--name-only", "--diff-filter=d", "HEAD")
    if tracked is None:
        tracked = file_list(root, "ls-files", "--cached") or []

    return inside(root, sorted(set(tracked) | set(untracked)))


def tree_hash(root):
    """Tree of the working directory as it is now, untracked files included."""
    index = git(root, "rev-parse", "--git-path", "index").stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "index"
        if index and (root / index).is_file():
            shutil.copy(root / index, scratch)

        env = {**os.environ, "GIT_INDEX_FILE": str(scratch)}
        if git(root, "add", "-A", env=env).returncode != 0:
            return None

        result = git(root, "write-tree", env=env)
        return result.stdout.strip() if result.returncode == 0 else None


def stamp_path(root):
    path = git(root, "rev-parse", "--git-path", STAMP_FILE).stdout.strip()
    return root / path if path else None


def run(root, line, timeout):
    """Output of a failing command, empty when it passed."""
    try:
        result = subprocess.run(line, shell=True, cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"timed out after {timeout}s"

    if result.returncode == 0:
        return ""

    output = (result.stdout + result.stderr).strip()
    return output[-OUTPUT_LIMIT:] or f"exit code {result.returncode}"


def run_all(root, commands, files, stage):
    problems = []
    for command in commands:
        line = expand(command, files)
        failure = run(root, line, TIMEOUT[stage]) if line else ""
        if failure:
            problems.append(f"after-edit: {line} failed:\n{failure}")

    return problems


def after_edit(call, root, config):
    problems = []
    for path in edited_files(call, root):
        problems += run_all(root, config.get(EDIT, []), [path], EDIT)

    if problems:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n\n".join(problems),
        }}))


def finish(root, config):
    """Run once per tree, so an unchanged tree never sends the agent back again."""
    commands = config.get(FINISH, [])
    stamp = stamp_path(root)
    if not commands or not stamp:
        return

    tree = tree_hash(root)
    last = stamp.read_text(encoding="utf-8") if stamp.is_file() else ""
    files = changed_files(root)
    if tree is None or tree == last or not files:
        return

    problems = run_all(root, commands, files, FINISH)
    stamp.write_text(tree_hash(root) or "", encoding="utf-8")
    if problems:
        print(json.dumps({"decision": "block", "reason": "\n\n".join(problems)}))


def main(argv):
    stage = argv[0] if argv else EDIT
    try:
        call = json.load(sys.stdin)
    except ValueError:
        call = {}

    call = call if isinstance(call, dict) else {}
    root = project_root(call)
    try:
        config = load_config(root)
    except SystemExit as error:
        if stage == EDIT:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": str(error)}}))
        else:
            print(error, file=sys.stderr)
        return 0

    if stage == FINISH:
        finish(root, config)
    else:
        after_edit(call, root, config)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
