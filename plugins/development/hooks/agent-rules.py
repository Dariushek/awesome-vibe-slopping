#!/usr/bin/env python3
"""Hold each subagent to the shell commands its role needs.

Reads a tool call as JSON on standard input. The `agent_type` field names the
subagent making it. Exit code 2 blocks the call and shows the message to the
agent. The main session and unknown agents are never restricted here.
"""

import json
import re
import shlex
import sys

BLOCKED = 2

# What each agent may do with the shell.
ONLY_READ_GIT = "only read git"
NO_GIT_CHANGES = "no git changes"
NO_PUSH = "no push"
RULES = {
    "rs-code-reviewer": ONLY_READ_GIT,
    "rs-verifier": NO_GIT_CHANGES,
    "rs-gate-runner": NO_GIT_CHANGES,
    "rs-task-implementer": NO_PUSH,
}
REASONS = {
    ONLY_READ_GIT: "This agent may run read-only git commands only, such as git diff, git log and git show.",
    NO_GIT_CHANGES: "This agent must not change the repository through git. It may run read-only git commands.",
    NO_PUSH: "This agent must never push. Report the commit and let the caller decide.",
}

READ_ONLY = {
    "diff", "log", "show", "status", "rev-parse", "merge-base", "blame", "ls-files", "ls-tree",
    "cat-file", "rev-list", "describe", "shortlog", "grep", "name-rev", "diff-tree", "for-each-ref",
    "show-ref",
}
# Subcommands that only read with these first arguments. "" stands for no argument.
READ_ONLY_WITH = {
    "branch": {"", "--show-current", "-a", "-r", "--list", "-v", "-vv"},
    "config": {"--get", "--list", "-l"},
    "worktree": {"list"},
    "stash": {"list"},
    "tag": {"", "-l", "--list"},
}
OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree"}
WRITES_A_FILE = "--output"
FILTERS = {"head", "tail", "wc", "grep", "sort", "uniq", "cat", "cut", "tr", "ls", "cd", "echo", "true"}

HEREDOC_BODY = re.compile(r"(?<=<<)-?\s*[\"']?(\w+)[\"']?[^\n]*\n.*?^\s*\1$", re.DOTALL | re.MULTILINE)
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
SEGMENT = re.compile(r"&&|\|\||[;|&\n]")
HARMLESS_REDIRECT = re.compile(r"\d?>&\d|\d?>\s*/dev/null")
REDIRECT = re.compile(r"^\d?>")
ASSIGNMENT = re.compile(r"^\w+=")


def segments(command):
    """Each simple command of a command line, commands inside $(...) included."""
    command = HARMLESS_REDIRECT.sub(" ", HEREDOC_BODY.sub("", command))
    inner = []
    while True:
        found = SUBSTITUTION.search(command)
        if not found:
            break

        inner.append(found.group(1) or found.group(2) or "")
        command = command[:found.start()] + " SUBSTITUTED " + command[found.end():]

    return [part for part in SEGMENT.split("\n".join([command, *inner])) if part.strip()]


def words(segment):
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()

    while tokens and ASSIGNMENT.match(tokens[0]):
        tokens.pop(0)

    return tokens


def git_arguments(tokens):
    """Subcommand and its arguments, global options left out."""
    rest = tokens[1:]
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in OPTIONS_WITH_VALUE else rest[1:]

    return rest


def reads_only(tokens):
    arguments = git_arguments(tokens)
    if not arguments or any(a.startswith(WRITES_A_FILE) for a in arguments):
        return False

    subcommand, first = arguments[0], (arguments[1] if len(arguments) > 1 else "")
    return subcommand in READ_ONLY or first in READ_ONLY_WITH.get(subcommand, ())


def allowed(rule, segment):
    tokens = words(segment)
    if not tokens:
        return True

    is_git = tokens[0] == "git"
    if rule == NO_PUSH:
        return not (is_git and git_arguments(tokens)[:1] == ["push"])

    if rule == ONLY_READ_GIT and any(REDIRECT.match(token) for token in tokens):
        return False

    if is_git:
        return reads_only(tokens)

    return rule == NO_GIT_CHANGES or tokens[0] in FILTERS


def agent_name(call):
    """Name without the plugin prefix: development:rs-verifier is rs-verifier."""
    return str(call.get("agent_type") or "").rsplit(":", 1)[-1]


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0

    if not isinstance(call, dict) or call.get("tool_name") != "Bash":
        return 0

    rule = RULES.get(agent_name(call))
    tool_input = call.get("tool_input")
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    if not rule or all(allowed(rule, segment) for segment in segments(command)):
        return 0

    print(f"Blocked: {REASONS[rule]}", file=sys.stderr)
    return BLOCKED


if __name__ == "__main__":
    sys.exit(main())
