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
# Other agents run the same hook under their own tool names. They cannot ask the user.
FOREIGN_TOOLS = {"exec": "Bash", "edit": "Edit", "write": "Write", "notebook_edit": "NotebookEdit"}
PATH_FIELDS = ("file_path", "notebook_path", "path", "target_file", "filename", "file")
CONTENT_FIELDS = ("content", "contents", "file_text", "text")
OLD_FIELDS = ("old_string", "old_str", "old_text")
NEW_FIELDS = ("new_string", "new_str", "new_text")
MANAGED_DIRS = ((".githooks",), (".claude", "hooks"), (".devin", "hooks"))
SETTINGS = ((".claude", "settings.json"), (".claude", "settings.local.json"), (".devin", "hooks.v1.json"))
VALIDATION = (".agents", "validation.json")
STAGES = ("commit", "push")
GUARD_COMMANDS = (".claude/hooks/guard", ".devin/hooks/guard")
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
MANAGED_PATH = re.compile(START + r"(\.githooks|\.claude/hooks|\.devin/hooks)(/|(?![\w.]))")
SETTINGS_PATH = re.compile(START + r"(\.claude/settings(\.local)?\.json|\.devin/hooks\.v1\.json)\b")
VALIDATION_PATH = re.compile(START + r"\.agents/validation\.json\b")
REDIRECT = re.compile(r">\s*[\"']?\S*$|>\s*[\"']?\S*(\.githooks|\.claude|\.agents|\.devin)/")

NO_VERIFY_REASON = (
    "--no-verify skips the validation hooks. Run the commit or push without it "
    "and fix what the hooks report."
)
HOOKS_PATH_REASON = (
    "core.hooksPath must stay on .githooks. Only `git config core.hooksPath .githooks` is allowed."
)
MANAGED_REASON = (
    ".githooks, .claude/hooks and .devin/hooks are managed by the harness. Change them in the harness "
    "repository and sync, never in the project."
)
SETTINGS_SHELL_REASON = (
    "Change the agent settings with the file editing tools, never from the shell, "
    "so the change can be checked."
)
GUARD_REASON = "This change would take the validation guard out of the settings. It must stay."
HOOKS_OFF_REASON = f"{HOOKS_OFF} would switch the validation guard off. It must stay on."
INVALID_SETTINGS_REASON = "This change would leave the settings as invalid JSON, which switches the guard off."
UNCHECKED_SETTINGS_REASON = "This change to the agent settings cannot be checked, so it is refused."
CANNOT_ASK_REASON = " This agent cannot ask for approval here, so stop and ask the user to make the change."
VALIDATION_UNCHECKED_REASON = "A change to .agents/validation.json needs the user's approval."
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


def first(fields, names):
    return next((str(fields[name]) for name in names if fields.get(name) is not None), "")


def replaced(text, edit):
    old, new = first(edit, OLD_FIELDS), first(edit, NEW_FIELDS)
    if not old or old not in text:
        return None

    return text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)


def resulting_text(tool, tool_input, before):
    """The file as the call would leave it, None when the call would fail or cannot be told."""
    if tool == "Write":
        return first(tool_input, CONTENT_FIELDS) if any(f in tool_input for f in CONTENT_FIELDS) else None

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
    lost_copy = any(command in before and command not in after for command in GUARD_COMMANDS)
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


def check_file(tool, tool_input, foreign):
    path = first(tool_input, PATH_FIELDS)
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
    if after is None and foreign:
        # The input fields of other agents are not all known. What cannot be read is not let through.
        raise Block(UNCHECKED_SETTINGS_REASON) if is_settings else Ask(VALIDATION_UNCHECKED_REASON)

    if after is None:
        return

    if is_settings:
        check_settings(before, after)
    else:
        check_validation(before, after)


def check(call):
    """Run the checks. An agent that cannot put a question to the user is refused instead."""
    name = call.get("tool_name")
    foreign = name in FOREIGN_TOOLS
    tool = FOREIGN_TOOLS.get(name, name)
    tool_input = call.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    try:
        if tool == "Bash":
            check_command(str(tool_input.get("command", "")))
        elif tool in FILE_TOOLS:
            check_file(tool, tool_input, foreign)
    except Ask as ask:
        if foreign:
            raise Block(f"{ask}{CANNOT_ASK_REASON}") from ask

        raise


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
