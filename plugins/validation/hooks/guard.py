#!/usr/bin/env python3
"""Refuse tool calls that would bypass or disable the validation hooks.

Reads the tool call as JSON on standard input. Exit code 2 blocks the call and
shows the message to the agent. Anything it cannot read is let through.
"""

import json
import re
import sys

BLOCKED = 2
HOOKS_DIR = ".githooks"
FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")

SEGMENT = re.compile(r"&&|\|\||[;|\n]")
# Text fed to a command, such as a commit message, is no command.
HEREDOC_BODY = re.compile(r"(?<=<<)-?\s*[\"']?(\w+)[\"']?[^\n]*\n.*?^\s*\1$", re.DOTALL | re.MULTILINE)
GIT = re.compile(r"\bgit\b")
NO_VERIFY = re.compile(r"(?<=\s)--no-verify\b")
COMMIT = re.compile(r"\bcommit\b")
SHORT_NO_VERIFY = re.compile(r"(?<=\s)-(?!-)[a-zA-Z]*n[a-zA-Z]*(?=\s|$)")
HOOKS_PATH = re.compile(r"core\.hookspath", re.IGNORECASE)
HOOKS_PATH_ALLOWED = (
    re.compile(r"\bconfig\s+(--local\s+)?core\.hookspath\s+\.githooks/?\s*$", re.IGNORECASE),
    re.compile(r"\bconfig\s+(--local\s+)?--get\s+core\.hookspath\s*$", re.IGNORECASE),
)
HOOK_FILE = re.compile(r"(^|[\s/\"'=])\.githooks(/|\b)")
CHANGES_FILES = re.compile(r"(^|\s)(rm|mv|cp|chmod|truncate|unlink|tee|sed|ln)\b")
REDIRECT_TO_HOOK = re.compile(r">\s*[\"']?(\S*/)?\.githooks/")

NO_VERIFY_REASON = (
    "--no-verify skips the validation hooks. Run the commit or push without it "
    "and fix what the hooks report."
)
HOOKS_PATH_REASON = (
    "core.hooksPath must stay on .githooks. Only `git config core.hooksPath .githooks` is allowed."
)
HOOK_FILE_REASON = (
    ".githooks is managed by the harness. Change the hooks in the harness repository and sync, "
    "never in the project."
)


def command_problem(command):
    for segment in SEGMENT.split(HEREDOC_BODY.sub("", command)):
        if GIT.search(segment):
            if NO_VERIFY.search(segment):
                return NO_VERIFY_REASON

            if COMMIT.search(segment) and SHORT_NO_VERIFY.search(segment):
                return NO_VERIFY_REASON

            if HOOKS_PATH.search(segment) and not any(p.search(segment.strip()) for p in HOOKS_PATH_ALLOWED):
                return HOOKS_PATH_REASON

        if HOOK_FILE.search(segment) and (CHANGES_FILES.search(segment) or REDIRECT_TO_HOOK.search(segment)):
            return HOOK_FILE_REASON

    return None


def file_problem(path):
    parts = re.split(r"[\\/]", path)
    return HOOK_FILE_REASON if HOOKS_DIR in parts[:-1] else None


def problem(call):
    tool = call.get("tool_name")
    tool_input = call.get("tool_input") or {}
    if tool == "Bash":
        return command_problem(str(tool_input.get("command", "")))

    if tool in FILE_TOOLS:
        return file_problem(str(tool_input.get("file_path") or tool_input.get("notebook_path") or ""))

    return None


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0

    reason = problem(call) if isinstance(call, dict) else None
    if not reason:
        return 0

    print(f"Blocked: {reason}", file=sys.stderr)
    return BLOCKED


if __name__ == "__main__":
    sys.exit(main())
