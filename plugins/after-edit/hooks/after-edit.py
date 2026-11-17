#!/usr/bin/env python3
"""Run the project's commands on a file the agent just wrote, such as a formatter.

Reads the tool call as JSON on standard input, from Claude Code or Devin. Commands come from
.agents/after-edit.json, a list of strings. `{changed}` becomes the edited
file, `{changed:*.cs,*.ts}` the file when it matches a pattern, and a command
whose placeholder matches nothing is skipped. `{python}` is this interpreter.
A failing command never blocks: its output goes back to the agent as context.
"""

import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CONFIG = Path(".agents") / "after-edit.json"
PATH_FIELDS = ("file_path", "notebook_path", "path", "target_file", "filename", "file")
# A patch names its files in headers, such as `*** Update File: src/a.cs`.
PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Move to): (.+?)\s*$", re.MULTILINE)
PROJECT_DIRS = ("CLAUDE_PROJECT_DIR", "DEVIN_PROJECT_DIR")
CHANGED = re.compile(r"\{changed(?::([^}]*))?\}")
CMD_VARIABLE = re.compile(r"%[^%]+%")
PYTHON = "{python}"
TIMEOUT = 60
OUTPUT_LIMIT = 2000


def quote(names, windows=os.name == "nt"):
    """Shell arguments. cmd.exe takes `&` and friends literally only inside double quotes."""
    if windows:
        return " ".join(f'"{name}"' for name in names)

    return shlex.join(names)


def matches(path, patterns):
    return not patterns or any(fnmatch.fnmatch(path, p.strip()) for p in patterns.split(","))


def expand(command, path):
    """The command for this file, None when a placeholder does not match it."""
    if not all(matches(path, patterns) for patterns in CHANGED.findall(command)):
        return None

    command = command.replace(PYTHON, quote([sys.executable]))
    return CHANGED.sub(lambda _: quote([path]), command)


def project_root(call):
    start = next((os.environ[v] for v in PROJECT_DIRS if os.environ.get(v)), None) or call.get("cwd") or os.getcwd()
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start, capture_output=True, text=True)
    return Path(result.stdout.strip() if result.returncode == 0 else start).resolve()


def commands(root):
    try:
        config = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except OSError:
        return []
    except ValueError as error:
        raise SystemExit(f"after-edit: {CONFIG}: invalid JSON: {error}") from error

    if not isinstance(config, list) or not all(isinstance(c, str) for c in config):
        raise SystemExit(f"after-edit: {CONFIG} must be a list of command strings")

    return config


def named_files(tool_input):
    names = [str(tool_input[f]) for f in PATH_FIELDS if tool_input.get(f)]
    for value in tool_input.values():
        if isinstance(value, str):
            names += PATCH_FILE.findall(value)

    return names


def edited_files(call, root):
    """The edited files relative to the root, posix style, without those outside it or gone."""
    tool_input = call.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    found = []
    for name in named_files(tool_input):
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


def run(root, line):
    """Output of a failing command, empty when it passed."""
    try:
        result = subprocess.run(line, shell=True, cwd=root, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"timed out after {TIMEOUT}s"

    if result.returncode == 0:
        return ""

    output = (result.stdout + result.stderr).strip()
    return output[-OUTPUT_LIMIT:] or f"exit code {result.returncode}"


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0

    if not isinstance(call, dict):
        return 0

    root = project_root(call)
    try:
        listed = commands(root)
    except SystemExit as error:
        problems = [str(error)]
    else:
        problems = []
        for path in edited_files(call, root):
            for command in listed:
                line = expand(command, path)
                failure = run(root, line) if line else ""
                if failure:
                    problems.append(f"after-edit: {line} failed:\n{failure}")

    if problems:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n\n".join(problems),
        }}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
