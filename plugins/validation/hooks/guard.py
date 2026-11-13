#!/usr/bin/env python3
"""Refuse tool calls that would bypass, disable or quietly weaken the validation gate.

Reads the tool call as JSON on standard input. Exit code 2 blocks the call and
shows the message to the agent. A decision printed as JSON asks the user first.
Anything it cannot read is let through.
"""

import json
import re
import sys
from pathlib import Path

BLOCKED = 2
FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
MANAGED_DIRS = ((".githooks",), (".claude", "hooks"))
SETTINGS = ((".claude", "settings.json"), (".claude", "settings.local.json"))
VALIDATION = (".agents", "validation.json")
STAGES = ("commit", "push")
GUARD_COMMAND = ".claude/hooks/guard"
GUARD_PLUGIN = "validation@"
HOOKS_OFF = "disableAllHooks"

# Text fed to a command, such as a commit message, is no command.
HEREDOC_BODY = re.compile(r"(?<=<<)-?\s*[\"']?(\w+)[\"']?[^\n]*\n.*?^\s*\1$", re.DOTALL | re.MULTILINE)
SEGMENT = re.compile(r"&&|\|\||[;|\n]")
GIT = re.compile(r"\bgit\b")
NO_VERIFY = re.compile(r"(?<=\s)--no-verify\b")
COMMIT = re.compile(r"\bcommit\b")
SHORT_NO_VERIFY = re.compile(r"(?<=\s)-(?!-)[a-zA-Z]*n[a-zA-Z]*(?=\s|$)")
HOOKS_PATH = re.compile(r"core\.hookspath", re.IGNORECASE)
HOOKS_PATH_ALLOWED = (
    re.compile(r"\bconfig\s+(--local\s+)?core\.hookspath\s+\.githooks/?\s*$", re.IGNORECASE),
    re.compile(r"\bconfig\s+(--local\s+)?--get\s+core\.hookspath\s*$", re.IGNORECASE),
)
CHANGES_FILES = re.compile(r"(^|\s)(rm|mv|cp|chmod|truncate|unlink|tee|sed|ln)\b")
START = r"(^|[\s/\"'=>])"
MANAGED_PATH = re.compile(START + r"(\.githooks|\.claude/hooks)(/|\b)")
SETTINGS_PATH = re.compile(START + r"\.claude/settings(\.local)?\.json\b")
VALIDATION_PATH = re.compile(START + r"\.agents/validation\.json\b")
REDIRECT = re.compile(r">\s*[\"']?\S*$|>\s*[\"']?\S*(\.githooks|\.claude|\.agents)/")

NO_VERIFY_REASON = (
    "--no-verify skips the validation hooks. Run the commit or push without it "
    "and fix what the hooks report."
)
HOOKS_PATH_REASON = (
    "core.hooksPath must stay on .githooks. Only `git config core.hooksPath .githooks` is allowed."
)
MANAGED_REASON = (
    ".githooks and .claude/hooks are managed by the harness. Change them in the harness "
    "repository and sync, never in the project."
)
SETTINGS_SHELL_REASON = (
    "Change the agent settings with the file editing tools, never from the shell, "
    "so the change can be checked."
)
GUARD_REASON = "This change would take the validation guard out of the settings. It must stay."
HOOKS_OFF_REASON = f"{HOOKS_OFF} would switch the validation guard off. It must stay on."
INVALID_SETTINGS_REASON = "This change would leave the settings as invalid JSON, which switches the guard off."
VALIDATION_SHELL_REASON = (
    "This command may change .agents/validation.json. Removing or changing a validation "
    "command needs the user's approval."
)


class Block(Exception):
    """The call must not run."""


class Ask(Exception):
    """The user decides whether the call runs."""


def changes(segment):
    return CHANGES_FILES.search(segment) or REDIRECT.search(segment)


def check_command(command):
    for segment in SEGMENT.split(HEREDOC_BODY.sub("", command)):
        if GIT.search(segment):
            if NO_VERIFY.search(segment):
                raise Block(NO_VERIFY_REASON)

            if COMMIT.search(segment) and SHORT_NO_VERIFY.search(segment):
                raise Block(NO_VERIFY_REASON)

            if HOOKS_PATH.search(segment) and not any(p.search(segment.strip()) for p in HOOKS_PATH_ALLOWED):
                raise Block(HOOKS_PATH_REASON)

        if not changes(segment):
            continue

        if MANAGED_PATH.search(segment):
            raise Block(MANAGED_REASON)

        if SETTINGS_PATH.search(segment):
            raise Block(SETTINGS_SHELL_REASON)

        if VALIDATION_PATH.search(segment):
            raise Ask(VALIDATION_SHELL_REASON)


def current_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""


def replaced(text, edit):
    old, new = str(edit.get("old_string", "")), str(edit.get("new_string", ""))
    if not old or old not in text:
        return None

    return text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)


def resulting_text(tool, tool_input, before):
    """The file as the call would leave it, None when the call would fail or cannot be told."""
    if tool == "Write":
        return str(tool_input.get("content", ""))

    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    text = before
    for edit in edits or []:
        text = replaced(text, edit) if isinstance(edit, dict) else None
        if text is None:
            return None

    return text


def parsed(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None

    return data if isinstance(data, dict) else None


def guard_plugins(settings):
    enabled = settings.get("enabledPlugins")
    enabled = enabled if isinstance(enabled, dict) else {}
    return {name for name, on in enabled.items() if on and name.startswith(GUARD_PLUGIN)}


def check_settings(before, after):
    settings = parsed(after)
    if settings is None:
        raise Block(INVALID_SETTINGS_REASON)

    if settings.get(HOOKS_OFF):
        raise Block(HOOKS_OFF_REASON)

    was = parsed(before) or {}
    lost_copy = GUARD_COMMAND in before and GUARD_COMMAND not in after
    if lost_copy or guard_plugins(was) - guard_plugins(settings):
        raise Block(GUARD_REASON)


def stage_commands(text):
    config = parsed(text) or {}
    commands = []
    for stage in STAGES:
        listed = config.get(stage)
        commands += [str(c) for c in listed] if isinstance(listed, list) else []

    return commands


def check_validation(before, after):
    kept = stage_commands(after)
    removed = [command for command in stage_commands(before) if command not in kept]
    if removed:
        listed = "; ".join(removed)
        raise Ask(f"This removes or changes validation commands, which needs your approval: {listed}")


def ends_with(parts, tail):
    return tuple(parts[-len(tail):]) == tail


def check_file(tool, tool_input):
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    parts = [part for part in re.split(r"[\\/]", path) if part]
    folder = parts[:-1]
    for managed in MANAGED_DIRS:
        if any(ends_with(folder[:end], managed) for end in range(len(managed), len(folder) + 1)):
            raise Block(MANAGED_REASON)

    is_settings = any(ends_with(parts, name) for name in SETTINGS)
    if not is_settings and not ends_with(parts, VALIDATION):
        return

    before = current_text(path)
    after = resulting_text(tool, tool_input, before)
    if after is None:
        return

    if is_settings:
        check_settings(before, after)
    else:
        check_validation(before, after)


def check(call):
    tool = call.get("tool_name")
    tool_input = call.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool == "Bash":
        check_command(str(tool_input.get("command", "")))
    elif tool in FILE_TOOLS:
        check_file(tool, tool_input)


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0

    if not isinstance(call, dict):
        return 0

    try:
        check(call)
    except Block as block:
        print(f"Blocked: {block}", file=sys.stderr)
        return BLOCKED
    except Ask as ask:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": str(ask),
        }}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
