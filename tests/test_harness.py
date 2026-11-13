"""Tests for bin/harness and the validation hook. Standard library only."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

# The scripts are loaded as modules below. Leave no bytecode next to them.
sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent
VALIDATE = REPO / "plugins" / "validation" / "githooks" / "validate"
GUARD = REPO / "plugins" / "validation" / "hooks" / "guard.py"
CHECK_SPECS = REPO / "plugins" / "development" / "githooks" / "check-specs"
AGENT_RULES = REPO / "plugins" / "development" / "hooks" / "agent-rules.py"
COMMIT_MESSAGE = REPO / "plugins" / "git" / "githooks" / "commit-message"

# The harness resolves user-level paths at import, so point home at a sandbox first.
HOME = tempfile.TemporaryDirectory()
os.environ["HOME"] = HOME.name
os.environ["USERPROFILE"] = HOME.name
os.environ.pop("APPDATA", None)

# Git exports GIT_DIR and friends to hooks. Drop them, or the tests would act on this repo.
for name in [n for n in os.environ if n.startswith("GIT_")]:
    del os.environ[name]

loader = SourceFileLoader("harness", str(REPO / "bin" / "harness"))
harness = module_from_spec(spec_from_loader("harness", loader))
loader.exec_module(harness)

loader = SourceFileLoader("validate", str(VALIDATE))
validate = module_from_spec(spec_from_loader("validate", loader))
loader.exec_module(validate)


def run(*argv):
    """Run a harness command, return its output and exit code."""
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            harness.main(list(argv))
        except SystemExit as error:
            code = error.code
            if isinstance(code, str):
                out.write(code)

    return out.getvalue(), code


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class ProjectCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.project = Path(tmp.name).resolve()
        self.addCleanup(self.forget)

    def forget(self):
        for path in (harness.PROJECTS_FILE, harness.GLOBAL_LOCK):
            path.unlink(missing_ok=True)

    def lock(self):
        return json.loads((self.project / harness.LOCK_FILE).read_text())


class BlockTest(ProjectCase):
    def test_block_is_added_after_existing_text(self):
        path = self.project / "AGENTS.md"
        path.write_text("# Mine\n")

        harness.upsert_block(path, "## Rules")

        self.assertTrue(path.read_text().startswith("# Mine\n\n<!-- harness:begin"))
        self.assertEqual(harness.read_block(path), "## Rules")

    def test_block_is_replaced_in_place(self):
        path = self.project / "AGENTS.md"
        path.write_text("# Mine\n")
        harness.upsert_block(path, "old")
        path.write_text(path.read_text() + "\ntail\n")

        harness.upsert_block(path, "new")

        text = path.read_text()
        self.assertEqual(harness.read_block(path), "new")
        self.assertEqual(text.count(harness.BLOCK_END), 1)
        self.assertTrue(text.endswith("tail\n"))

    def test_empty_body_removes_block_and_keeps_the_rest(self):
        path = self.project / "AGENTS.md"
        path.write_text("# Mine\n")
        harness.upsert_block(path, "body")

        harness.upsert_block(path, "")

        self.assertEqual(path.read_text(), "# Mine\n")


class SyncTest(ProjectCase):
    def test_sync_writes_rules_skills_and_lock(self):
        _, code = run("sync", str(self.project), "docs")

        self.assertEqual(code, 0)
        self.assertIn("## README", (self.project / "AGENTS.md").read_text())
        self.assertTrue((self.project / ".agents/skills/rs-readme/SKILL.md").is_file())
        self.assertTrue((self.project / ".claude/skills/rs-readme/SKILL.md").is_file())
        self.assertEqual((self.project / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertEqual(self.lock()["bundles"], ["docs"])

    def test_dependencies_are_added_but_not_saved(self):
        out, _ = run("sync", str(self.project), "development")

        self.assertIn("add git: required by development", out)
        self.assertTrue((self.project / ".agents/skills/commit-message/SKILL.md").is_file())
        self.assertTrue((self.project / ".agents/skills/playwright/SKILL.md").is_file())
        self.assertEqual(self.lock()["bundles"], ["development"])

    def test_dependency_installed_globally_is_not_copied(self):
        harness.write_json(harness.GLOBAL_LOCK, {"bundles": ["git", "browser"]})

        out, _ = run("sync", str(self.project), "development")

        self.assertNotIn("required by", out)
        self.assertFalse((self.project / ".agents/skills/commit-message").exists())

    def test_global_bundle_with_rules_warns(self):
        harness.write_json(harness.GLOBAL_LOCK, {"bundles": ["coding"]})

        out, _ = run("sync", str(self.project), "coding")

        self.assertIn("warning: coding is installed globally", out)

    def test_exclusive_bundles_are_refused(self):
        out, code = run("sync", str(self.project), "architecture", "architecture-light")

        self.assertNotEqual(code, 0)
        self.assertIn("Pick one of", out)

    def test_edited_file_is_kept_unless_forced(self):
        run("sync", str(self.project), "docs")
        skill = self.project / ".agents/skills/rs-readme/SKILL.md"
        original = skill.read_text()
        skill.write_text("mine")

        out, _ = run("sync", str(self.project))
        self.assertIn("skip .agents/skills/rs-readme/SKILL.md", out)
        self.assertEqual(skill.read_text(), "mine")

        run("sync", str(self.project), "--force")
        self.assertEqual(skill.read_text(), original)

    def test_dropped_bundle_files_are_removed(self):
        run("sync", str(self.project), "docs", "git")

        run("sync", str(self.project), "git")

        self.assertFalse((self.project / ".agents/skills/rs-readme").exists())
        self.assertTrue((self.project / ".agents/skills/commit-message/SKILL.md").is_file())
        self.assertNotIn("## README", (self.project / "AGENTS.md").read_text())

    def test_dry_run_writes_nothing(self):
        out, code = run("sync", str(self.project), "docs", "--dry-run")

        self.assertEqual(code, 0)
        self.assertIn("would write", out)
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertFalse(harness.PROJECTS_FILE.exists())

    def test_hooks_are_synced_and_activated(self):
        git(self.project, "init", "-q")

        run("sync", str(self.project), "validation")

        hook = self.project / ".githooks/pre-commit"
        self.assertTrue(hook.is_file())
        path = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=self.project, capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(path, ".githooks")

    def agent_hook_commands(self):
        settings = json.loads((self.project / ".claude/settings.json").read_text())
        return [
            hook["command"]
            for group in settings.get("hooks", {}).get("PreToolUse", [])
            for hook in group["hooks"]
        ]

    def test_copy_target_installs_the_agent_hooks_of_a_bundle(self):
        run("sync", str(self.project), "validation")

        self.assertTrue((self.project / ".claude/hooks/guard.py").is_file())
        self.assertFalse((self.project / ".claude/hooks/hooks.json").exists())
        self.assertEqual(self.agent_hook_commands(), ['sh "$CLAUDE_PROJECT_DIR/.claude/hooks/guard"'])

    def test_resync_keeps_the_projects_own_agent_hooks_and_adds_ours_once(self):
        own = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "mine"}]}]}}
        (self.project / ".claude").mkdir()
        (self.project / ".claude/settings.json").write_text(json.dumps(own))

        run("sync", str(self.project), "validation")
        run("sync", str(self.project))

        self.assertEqual(self.agent_hook_commands(), ["mine", 'sh "$CLAUDE_PROJECT_DIR/.claude/hooks/guard"'])

    def devin_hooks(self):
        return json.loads((self.project / ".devin/hooks.v1.json").read_text())

    def test_devin_target_registers_the_guard_under_devins_tool_names(self):
        run("sync", str(self.project), "validation", "--targets", "agents,devin")

        self.assertTrue((self.project / ".devin/hooks/guard.py").is_file())
        self.assertFalse((self.project / ".devin/hooks/devin.json").exists())
        self.assertFalse((self.project / ".claude/hooks").exists())
        (group,) = self.devin_hooks()["PreToolUse"]
        self.assertEqual(group["hooks"][0]["command"], 'sh "${DEVIN_PROJECT_DIR:-.}/.devin/hooks/guard"')
        for tool in ("exec", "edit", "write", "apply_patch"):
            self.assertRegex(tool, group["matcher"])

    def test_devin_target_keeps_the_projects_own_hooks_and_adds_ours_once(self):
        own = {"PreToolUse": [{"matcher": "exec", "hooks": [{"type": "command", "command": "mine"}]}]}
        (self.project / ".devin").mkdir()
        (self.project / ".devin/hooks.v1.json").write_text(json.dumps(own))

        run("sync", str(self.project), "validation", "--targets", "agents,devin")
        run("sync", str(self.project))

        commands = [hook["command"] for group in self.devin_hooks()["PreToolUse"] for hook in group["hooks"]]
        self.assertEqual(commands, ["mine", 'sh "${DEVIN_PROJECT_DIR:-.}/.devin/hooks/guard"'])

    def test_bundle_without_devin_hooks_leaves_nothing_for_devin(self):
        run("sync", str(self.project), "docs", "--targets", "agents,devin")

        self.assertFalse((self.project / ".devin").exists())

    def test_remove_takes_the_devin_hooks_out_again(self):
        run("sync", str(self.project), "validation", "--targets", "agents,devin")

        run("remove", str(self.project))

        self.assertFalse((self.project / ".devin").exists())

    def test_new_project_is_synced_for_devin_by_default(self):
        run("sync", str(self.project), "validation")

        self.assertTrue((self.project / ".devin/hooks.v1.json").is_file())
        self.assertEqual(self.agent_hook_commands(), ['sh "$CLAUDE_PROJECT_DIR/.claude/hooks/guard"'])

    def test_remove_takes_the_agent_hooks_out_again(self):
        run("sync", str(self.project), "validation")

        run("remove", str(self.project))

        self.assertFalse((self.project / ".claude/hooks/guard.py").exists())
        self.assertFalse((self.project / ".claude/settings.json").exists())

    def test_git_hooks_of_a_globally_installed_dependency_are_still_synced(self):
        harness.write_json(harness.GLOBAL_LOCK, {"bundles": ["git", "browser"]})
        git(self.project, "init", "-q")

        run("sync", str(self.project), "development")

        self.assertTrue((self.project / ".githooks/commit-msg").is_file())
        self.assertFalse((self.project / ".agents/skills/commit-message").exists())

    def test_status_is_up_to_date_with_git_hooks_of_a_global_dependency(self):
        harness.write_json(harness.GLOBAL_LOCK, {"bundles": ["git", "browser"]})
        git(self.project, "init", "-q")
        run("sync", str(self.project), "development")

        out, _ = run("status", str(self.project))

        self.assertIn("up to date", out)

    def test_bytecode_caches_next_to_the_hooks_are_not_synced(self):
        cache = harness.PLUGINS_DIR / "validation" / "githooks" / "__pycache__"
        cache.mkdir(exist_ok=True)
        self.addCleanup(shutil.rmtree, cache, ignore_errors=True)
        (cache / "validate.cpython-313.pyc").write_bytes(b"cache")
        git(self.project, "init", "-q")

        run("sync", str(self.project), "validation")

        self.assertFalse((self.project / ".githooks/__pycache__").exists())

    def test_sync_all_resyncs_registered_projects(self):
        run("sync", str(self.project), "docs")
        skill = self.project / ".agents/skills/rs-readme/SKILL.md"
        skill.unlink()

        out, _ = run("sync", "--all")

        self.assertIn(f"Synced docs into {self.project}", out)
        self.assertTrue(skill.is_file())

    def test_status_reports_missing_and_edited(self):
        run("sync", str(self.project), "docs")
        out, _ = run("status", str(self.project))
        self.assertIn("up to date", out)

        (self.project / ".agents/skills/rs-readme/SKILL.md").write_text("mine")
        (self.project / ".claude/skills/rs-readme/SKILL.md").unlink()
        out, _ = run("status", str(self.project))

        self.assertIn("edited locally: .agents/skills/rs-readme/SKILL.md", out)
        self.assertIn("missing: .claude/skills/rs-readme/SKILL.md", out)

    def test_remove_takes_everything_out_but_user_content(self):
        (self.project / "AGENTS.md").write_text("# Mine\n")
        run("sync", str(self.project), "docs")

        run("remove", str(self.project))

        self.assertEqual((self.project / "AGENTS.md").read_text(), "# Mine\n")
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / harness.LOCK_FILE).exists())
        self.assertEqual(harness.registered_projects(), [])


class GlobalTest(ProjectCase):
    def setUp(self):
        super().setUp()
        self.claude = Path(HOME.name) / ".claude"
        self.claude.mkdir(exist_ok=True)

    def test_global_installs_and_removes(self):
        run("global", "communication", "git")

        rules = self.claude / "CLAUDE.md"
        skill = self.claude / "skills/commit-message/SKILL.md"
        self.assertIn("## Communication", rules.read_text())
        self.assertTrue(skill.is_file())

        run("remove", "--global")

        self.assertNotIn("## Communication", rules.read_text())
        self.assertFalse(skill.exists())
        self.assertFalse(harness.GLOBAL_LOCK.exists())


class CheckTest(unittest.TestCase):
    def test_repo_passes_its_own_check(self):
        problems = []
        names = harness.bundle_names()
        skills = {p.parent.name for p in harness.PLUGINS_DIR.glob("*/skills/*/SKILL.md")}
        agents = {p.stem for p in harness.PLUGINS_DIR.glob("*/agents/*.md")}
        for name in names:
            harness.check_bundle(name, names, skills, agents, problems)
        harness.check_marketplace(names, problems)

        self.assertEqual([p for p in problems if "bump version" not in p], [])

    def test_unknown_skill_reference_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "rule.md").write_text("Run rs-spec, then rs-nonexistent.")
            problems = []

            harness.check_references(Path(tmp), {"rs-spec"}, problems)

        self.assertEqual(len(problems), 1)
        self.assertIn("rs-nonexistent", problems[0])


class ValidateHookTest(ProjectCase):
    def setUp(self):
        super().setUp()
        git(self.project, "init", "-q")
        (self.project / ".agents").mkdir()

    def validate(self, config, stage="commit", env=None):
        (self.project / ".agents/validation.json").write_text(config)
        return subprocess.run(
            [sys.executable, str(VALIDATE), stage],
            cwd=self.project, capture_output=True, text=True, env=env,
        )

    def command(self, code):
        return f'"{sys.executable}" -c "import sys; print(\'ran\'); sys.exit({code})"'

    def test_passing_stage_is_skipped_until_the_tree_changes(self):
        config = json.dumps({"commit": [self.command(0)]})

        self.assertIn("ran", self.validate(config).stdout)
        self.assertIn("skipped", self.validate(config).stdout)

        (self.project / "new.txt").write_text("x")
        self.assertIn("ran", self.validate(config).stdout)

    def test_failing_command_fails_the_stage(self):
        result = self.validate(json.dumps({"commit": [self.command(3)]}))

        self.assertEqual(result.returncode, 1)
        self.assertIn("failed", result.stderr)

    def test_string_instead_of_list_is_refused(self):
        result = self.validate('{"commit": "true"}')

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be a list of command strings", result.stderr)

    def test_invalid_json_is_refused(self):
        result = self.validate("{")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid JSON", result.stderr)

    def echo(self, placeholder):
        return f'"{sys.executable}" -c "import sys; print(\'got\', ascii(sys.argv[1:]))" {placeholder}'

    def commit_all(self):
        git(self.project, "add", "-A")
        git(self.project, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")

    def test_changed_placeholder_gets_only_changed_files_matching_the_pattern(self):
        for name in ("old.py", "edited.py", "gone.py"):
            (self.project / name).write_text("x")
        self.commit_all()
        (self.project / "edited.py").write_text("y")
        (self.project / "gone.py").unlink()
        (self.project / "new file.py").write_text("x")
        (self.project / "new.txt").write_text("x")

        result = self.validate(json.dumps({"commit": [self.echo("{changed:*.py}")]}))

        self.assertIn("got ['edited.py', 'new file.py']", result.stdout)

    def test_changed_file_with_special_characters_stays_one_argument(self):
        for name in ("caf\u00e9 menu.py", "a&b.py"):
            (self.project / name).write_text("x")

        result = self.validate(json.dumps({"commit": [self.echo("{changed:*.py}")]}))

        self.assertIn("got ['a&b.py', 'caf\\xe9 menu.py']", result.stdout)

    def test_file_name_the_console_cannot_print_does_not_stop_the_run(self):
        (self.project / "za\u017c\u00f3\u0142\u0107.py").write_text("x")
        console = {**os.environ, "PYTHONIOENCODING": "ascii"}

        result = self.validate(json.dumps({"commit": [self.echo("{changed:*.py}")]}), env=console)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("got ['za\\u017c\\xf3\\u0142\\u0107.py']", result.stdout)

    def test_python_placeholder_runs_the_interpreter_of_the_hook(self):
        command = '{python} -c "import sys; print(\'ran with\', sys.executable)"'

        result = self.validate(json.dumps({"commit": [command]}))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"ran with {sys.executable}", result.stdout)

    def test_changed_placeholder_without_pattern_gets_every_changed_file(self):
        (self.project / "old.py").write_text("x")
        self.commit_all()
        (self.project / "new.txt").write_text("x")

        result = self.validate(json.dumps({"commit": [self.echo("{changed}")]}))

        self.assertIn("got ['.agents/validation.json', 'new.txt']", result.stdout)

    def test_command_with_no_changed_files_is_skipped(self):
        (self.project / "old.py").write_text("x")
        self.commit_all()

        result = self.validate(json.dumps({"commit": [self.echo("{changed:*.py}")]}))

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("got [", result.stdout)
        self.assertIn("no changed files", result.stdout)

    def test_changed_placeholder_gets_every_file_before_the_first_commit(self):
        (self.project / "first.py").write_text("x")

        result = self.validate(json.dumps({"commit": [self.echo("{changed:*.py}")]}))

        self.assertIn("got ['first.py']", result.stdout)

    def test_push_stage_gets_files_changed_since_the_upstream_branch(self):
        (self.project / "old.py").write_text("x")
        self.commit_all()
        git(self.project, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(self.project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        (self.project / "pushed.py").write_text("x")
        self.commit_all()
        (self.project / "pending.py").write_text("x")

        result = self.validate(json.dumps({"push": [self.echo("{changed:*.py}")]}), stage="push")

        self.assertIn("got ['pending.py', 'pushed.py']", result.stdout)


class ExpandTest(unittest.TestCase):
    def test_long_file_list_is_split_over_several_runs(self):
        limit = validate.MAX_ARGUMENTS_LENGTH
        self.addCleanup(setattr, validate, "MAX_ARGUMENTS_LENGTH", limit)
        validate.MAX_ARGUMENTS_LENGTH = 8

        files = ["aaaa.py", "bbbb.py", "cccc.py"]

        lines = validate.expand("lint {changed}", files)

        self.assertEqual(lines, [f"lint {validate.quote([name])}" for name in files])

    def test_each_placeholder_gets_its_own_files(self):
        lines = validate.expand("lint {changed:*.py} --css {changed:*.css,*.scss}", ["a.py", "b.css", "c.scss"])

        python, styles = validate.quote(["a.py"]), validate.quote(["b.css", "c.scss"])
        self.assertEqual(lines, [f"lint {python} --css {styles}"])

    def test_posix_shell_gets_a_name_with_a_space_as_one_argument(self):
        self.assertEqual(validate.quote(["my file.py", "a.py"], windows=False), "'my file.py' a.py")

    def test_windows_shell_gets_every_name_in_double_quotes(self):
        quoted = validate.quote(["my file.py", "src/a&b.py", "100%.py"], windows=True)

        self.assertEqual(quoted, '"my file.py" "src/a&b.py" "100%.py"')

    def test_windows_shell_refuses_a_name_it_would_expand_as_a_variable(self):
        with self.assertRaises(SystemExit) as refused:
            validate.quote(["my%PATH%.py"], windows=True)

        self.assertIn("my%PATH%.py", str(refused.exception))


class CommitMessageHookTest(ProjectCase):
    def setUp(self):
        super().setUp()
        git(self.project, "init", "-q", "-b", "main")

    def check(self, message, branch=None):
        if branch:
            git(self.project, "checkout", "-q", "-b", branch)

        path = self.project / "message.txt"
        path.write_text(message, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(COMMIT_MESSAGE), str(path)],
            cwd=self.project, capture_output=True, text=True,
        )

    def assert_refused(self, result, reason):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)

    def test_message_following_the_rules_is_accepted(self):
        result = self.check("Retry token refresh on clock skew\n\nRefresh failed when the server clock ran ahead.\n")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_subject_longer_than_72_characters_is_refused(self):
        self.assert_refused(self.check("A" + "b" * 72), "72")

    def test_subject_starting_in_lower_case_is_refused(self):
        self.assert_refused(self.check("retry token refresh"), "capital")

    def test_subject_ending_with_a_period_is_refused(self):
        self.assert_refused(self.check("Retry token refresh."), "period")

    def test_body_right_after_the_subject_is_refused(self):
        self.assert_refused(self.check("Retry token refresh\nRefresh failed."), "blank line")

    def test_body_line_longer_than_200_characters_is_refused(self):
        self.assert_refused(self.check("Retry token refresh\n\n" + "word " * 41), "200")

    def test_body_line_of_200_characters_is_accepted(self):
        result = self.check("Retry token refresh\n\n" + "word " * 39 + "words")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_long_body_line_that_cannot_be_wrapped_is_accepted(self):
        result = self.check("Retry token refresh\n\nSee https://example.com/" + "a" * 80)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_co_author_trailer_is_refused(self):
        message = "Retry token refresh\n\nCo-authored-by: Someone <someone@example.com>\n"

        self.assert_refused(self.check(message), "Co-Authored-By")

    def test_generated_with_line_is_refused(self):
        self.assert_refused(self.check("Retry token refresh\n\nGenerated with a tool\n"), "Generated with")

    def test_subject_without_the_task_number_of_the_branch_is_refused(self):
        self.assert_refused(self.check("Retry token refresh", branch="feature/4821-token-refresh"), "#4821")

    def test_subject_with_the_task_number_of_the_branch_is_accepted(self):
        result = self.check("#4821 Retry token refresh", branch="feature/4821-token-refresh")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_number_inside_a_branch_word_is_no_task_number(self):
        result = self.check("Retry token refresh", branch="feature/oauth2-login")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_merge_commit_is_not_checked(self):
        result = self.check("Merge branch 'feature/some-very-long-branch-name' of example.com:team/repository into main.")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_comment_lines_git_adds_are_ignored(self):
        result = self.check("Retry token refresh\n# Please enter the commit message for your changes. Lines starting\n")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_project_with_its_own_format_keeps_only_the_attribution_check(self):
        overrides = self.project / ".agents" / "overrides"
        overrides.mkdir(parents=True)
        (overrides / "commit-message.md").write_text("Use conventional commits.")

        self.assertEqual(self.check("fix: retry token refresh.").returncode, 0)
        self.assert_refused(self.check("fix: retry\n\nCo-Authored-By: X <x@example.com>"), "Co-Authored-By")


class GuardTest(unittest.TestCase):
    BLOCKED = 2

    def call(self, tool, **tool_input):
        return subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
            capture_output=True, text=True,
        )

    def assert_blocked(self, result, reason):
        self.assertEqual(result.returncode, self.BLOCKED, result.stderr)
        self.assertIn(reason, result.stderr)

    def assert_allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_commit_with_no_verify_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="git commit --no-verify -m x"), "--no-verify")

    def test_push_with_no_verify_after_another_command_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="git add -A && git push --no-verify"), "--no-verify")

    def test_commit_with_the_short_no_verify_flag_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="git commit -anm x"), "--no-verify")

    def test_plain_commit_is_allowed(self):
        self.assert_allowed(self.call("Bash", command="git add -A && git commit -q -F - <<'EOF'\nSubject\nEOF"))

    def test_dry_run_push_is_allowed(self):
        self.assert_allowed(self.call("Bash", command="git push -n origin main"))

    def test_no_verify_in_a_message_on_a_later_line_is_allowed(self):
        command = "git commit -F - <<'EOF'\nExplain why --no-verify is refused\nEOF"

        self.assert_allowed(self.call("Bash", command=command))

    def test_git_command_quoted_in_a_message_is_allowed(self):
        command = "git commit -F - <<'EOF'\nRefuse git commit --no-verify\n\nAnd rm .githooks/validate too.\nEOF"

        self.assert_allowed(self.call("Bash", command=command))

    def test_command_after_a_message_is_still_checked(self):
        command = "git commit -F - <<'EOF'\nSubject\nEOF\ngit push --no-verify"

        self.assert_blocked(self.call("Bash", command=command), "--no-verify")

    def test_pointing_hooks_path_elsewhere_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="git config core.hooksPath /dev/null"), "core.hooksPath")

    def test_unsetting_hooks_path_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="git config --unset core.hooksPath"), "core.hooksPath")

    def test_hooks_path_for_one_command_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="git -c core.hooksPath=/tmp commit -m x"), "core.hooksPath")

    def test_setting_hooks_path_to_the_hooks_directory_is_allowed(self):
        self.assert_allowed(self.call("Bash", command="git config core.hooksPath .githooks"))

    def test_reading_hooks_path_is_allowed(self):
        self.assert_allowed(self.call("Bash", command="git config --get core.hooksPath"))

    def test_deleting_a_hook_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="rm -f .githooks/pre-commit"), ".githooks")

    def test_overwriting_a_hook_from_the_shell_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="echo 'exit 0' > .githooks/validate"), ".githooks")

    def test_running_the_gate_is_allowed(self):
        self.assert_allowed(self.call("Bash", command=".githooks/validate commit 2>&1 | tail -5"))

    def test_editing_a_hook_file_is_blocked(self):
        self.assert_blocked(self.call("Edit", file_path="/work/project/.githooks/validate"), ".githooks")

    def test_editing_another_file_is_allowed(self):
        self.assert_allowed(self.call("Write", file_path="/work/project/src/app.py"))

    def test_input_that_is_no_json_is_allowed(self):
        result = subprocess.run([sys.executable, str(GUARD)], input="not json", capture_output=True, text=True)

        self.assert_allowed(result)


class GuardedFilesTest(ProjectCase):
    BLOCKED = 2
    GUARD_HOOK = {"type": "command", "command": 'sh "$CLAUDE_PROJECT_DIR/.claude/hooks/guard"'}

    def setUp(self):
        super().setUp()
        self.settings = self.write(".claude/settings.json", json.dumps({
            "permissions": {"allow": ["Bash(ls:*)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [self.GUARD_HOOK]}]},
        }, indent=2))
        self.validation = self.write(".agents/validation.json", json.dumps({
            "commit": ["build", "test"], "push": ["slow test"],
        }, indent=2))

    def write(self, rel, text):
        path = self.project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def call(self, tool, **tool_input):
        return subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": str(self.project)}),
            capture_output=True, text=True,
        )

    def assert_blocked(self, result, reason):
        self.assertEqual(result.returncode, self.BLOCKED, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)

    def assert_allowed(self, result):
        self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)

    def assert_asks(self, result, reason):
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertIn(reason, decision["permissionDecisionReason"])

    def test_editing_an_agent_hook_script_is_blocked(self):
        path = str(self.project / ".claude/hooks/guard.py")

        self.assert_blocked(self.call("Edit", file_path=path, old_string="a", new_string="b"), ".claude/hooks")

    def test_deleting_the_agent_hooks_from_the_shell_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="rm -rf .claude/hooks"), ".claude/hooks")

    def test_taking_the_guard_out_of_the_settings_is_blocked(self):
        command = json.dumps(self.GUARD_HOOK["command"])

        result = self.call("Edit", file_path=str(self.settings), old_string=command, new_string='"true"')

        self.assert_blocked(result, "guard")

    def test_overwriting_the_settings_without_the_guard_is_blocked(self):
        self.assert_blocked(self.call("Write", file_path=str(self.settings), content="{}"), "guard")

    def test_other_changes_to_the_settings_are_allowed(self):
        result = self.call("Edit", file_path=str(self.settings), old_string="Bash(ls:*)", new_string="Bash(cat:*)")

        self.assert_allowed(result)

    def test_switching_all_hooks_off_is_blocked(self):
        local = str(self.project / ".claude/settings.local.json")

        self.assert_blocked(self.call("Write", file_path=local, content='{"disableAllHooks": true}'), "disableAllHooks")

    def test_overwriting_the_settings_from_the_shell_is_blocked(self):
        self.assert_blocked(self.call("Bash", command="echo '{}' > .claude/settings.json"), "settings")

    def test_removing_a_validation_command_asks_the_user(self):
        result = self.call("Edit", file_path=str(self.validation), old_string='"build",', new_string="")

        self.assert_asks(result, "build")

    def test_changing_a_validation_command_asks_the_user(self):
        result = self.call("Edit", file_path=str(self.validation), old_string='"slow test"', new_string='"true"')

        self.assert_asks(result, "slow test")

    def test_adding_a_validation_command_is_allowed(self):
        result = self.call("Edit", file_path=str(self.validation), old_string='"test"', new_string='"test", "lint"')

        self.assert_allowed(result)

    def test_overwriting_the_validation_commands_with_fewer_asks_the_user(self):
        result = self.call("Write", file_path=str(self.validation), content='{"commit": ["build"]}')

        self.assert_asks(result, "test")

    def test_changing_the_validation_file_from_the_shell_asks_the_user(self):
        self.assert_asks(self.call("Bash", command="sed -i s/test/true/ .agents/validation.json"), "validation.json")

    def test_reading_the_validation_file_is_allowed(self):
        self.assert_allowed(self.call("Bash", command="cat .agents/validation.json"))

    def test_devin_shell_command_skipping_the_hooks_is_blocked(self):
        self.assert_blocked(self.call("exec", command="git commit --no-verify -m x", shell_id="main"), "--no-verify")

    def test_devin_plain_shell_command_is_allowed(self):
        self.assert_allowed(self.call("exec", command="git status", shell_id="main"))

    def test_devin_edit_of_a_hook_is_blocked_whatever_the_path_field_is_called(self):
        hook = str(self.project / ".githooks/validate")
        for field in ("file_path", "path", "target_file"):
            self.assert_blocked(self.call("edit", **{field: hook}), ".githooks")

    def test_devin_write_dropping_a_validation_command_is_blocked_since_it_cannot_ask(self):
        result = self.call("write", file_path=str(self.validation), content='{"commit": ["build"]}')

        self.assert_blocked(result, "ask the user")

    def test_devin_write_adding_a_validation_command_is_allowed(self):
        content = json.dumps({"commit": ["build", "test", "lint"], "push": ["slow test"]})

        self.assert_allowed(self.call("write", file_path=str(self.validation), content=content))

    def test_devin_edit_of_the_validation_file_that_cannot_be_read_is_blocked(self):
        self.assert_blocked(self.call("edit", file_path=str(self.validation), unknown_field="x"), "ask the user")

    def test_devin_edit_of_the_settings_that_cannot_be_read_is_blocked(self):
        self.assert_blocked(self.call("edit", file_path=str(self.settings), unknown_field="x"), "cannot be checked")

    def test_editing_a_devin_hook_script_is_blocked(self):
        path = str(self.project / ".devin/hooks/guard.py")

        self.assert_blocked(self.call("edit", file_path=path), ".devin/hooks")

    def test_taking_the_guard_out_of_the_devin_hooks_is_blocked(self):
        registered = {"PreToolUse": [{"matcher": "exec", "hooks": [{"type": "command", "command": "sh .devin/hooks/guard"}]}]}
        path = self.write(".devin/hooks.v1.json", json.dumps(registered))

        self.assert_blocked(self.call("write", file_path=str(path), content="{}"), "guard")
        self.assert_blocked(self.call("exec", command="rm .devin/hooks.v1.json"), "settings")

    def test_devin_tool_the_guard_does_not_know_is_allowed(self):
        self.assert_allowed(self.call("write_to_process", input="y"))

    def test_first_validation_file_is_allowed(self):
        self.validation.unlink()

        result = self.call("Write", file_path=str(self.validation), content='{"commit": ["build"]}')

        self.assert_allowed(result)


SPEC = """# Place order

- Date: 2026-01-10
- Status: Approved
- Prototype: Not applicable

## Scenarios

### S1. Valid widget order is placed

Given widget W1234 costs 10.00 in the catalog
When a customer orders 3 of W1234
Then the order is placed with amount to bill 30.00

### S2. Invoice prints on one page

Given an order with 12 lines
When staff prints its invoice
Then all 12 lines fit on one A4 page
Verified by: manual. Print to PDF and count pages. Reason: depends on the printer driver.

## Checks

- C1: The app builds with no warnings. Verified by: command `build`.

## Non-functional requirements

- N1: Placing an order responds within 1 s. Verified by: load test.
"""

PLAN = """# Plan: Place order

- Spec: [SPEC.md](SPEC.md)
- Branch: feat/place-order
- Status: Approved

## Tasks

| ID | Title | Depends on | Status |
|----|-------|------------|--------|
| T1 | Place the order | - | done |
| T2 | Print the invoice | T1 | todo |

## T1. Place the order

- Goal: orders can be placed.
- Files: src/orders.py
- Scenarios: S1
- Requirements: N1
- Checks: C1
- Model: default

## T2. Print the invoice

- Goal: invoices print.
- Files: src/invoice.py
- Scenarios: S2
- Model: small
"""


class CheckSpecsTest(ProjectCase):
    def check(self, spec=SPEC, plan=PLAN, *args):
        folder = self.project / "docs/specs/2026-01-10-place-order"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SPEC.md").write_text(spec)
        if plan:
            (folder / "PLAN.md").write_text(plan)

        return subprocess.run(
            [sys.executable, str(CHECK_SPECS), *args],
            cwd=self.project, capture_output=True, text=True,
        )

    def assert_refused(self, result, reason):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)

    def test_complete_spec_and_plan_pass(self):
        result = self.check()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_project_without_specs_passes(self):
        result = subprocess.run([sys.executable, str(CHECK_SPECS)], cwd=self.project, capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_status_is_refused(self):
        self.assert_refused(self.check(SPEC.replace("Status: Approved", "Status: Ready")), "Status must be")

    def test_approved_spec_with_an_unknown_is_refused(self):
        self.assert_refused(self.check(SPEC.replace("costs 10.00", "costs ???")), "???")

    def test_draft_spec_may_hold_unknowns(self):
        spec = SPEC.replace("Status: Approved", "Status: Draft").replace("costs 10.00", "costs ???")

        self.assertEqual(self.check(spec, None).returncode, 0)

    def test_scenario_id_used_twice_is_refused(self):
        self.assert_refused(self.check(SPEC.replace("### S2.", "### S1.")), "S1 is used twice")

    def test_check_without_a_verification_method_is_refused(self):
        self.assert_refused(self.check(SPEC.replace(" Verified by: command `build`.", "")), "C1 has no `Verified by`")

    def test_scenario_with_an_unknown_method_is_refused(self):
        self.assert_refused(self.check(SPEC.replace("Verified by: manual.", "Verified by: looking.")), "S2")

    def test_manual_scenario_without_steps_is_refused(self):
        spec = SPEC.replace(" Print to PDF and count pages. Reason: depends on the printer driver.", "")

        self.assert_refused(self.check(spec), "S2")

    def test_approved_plan_of_a_draft_spec_is_refused(self):
        self.assert_refused(self.check(SPEC.replace("Status: Approved", "Status: Draft")), "spec is not Approved")

    def test_approved_plan_without_a_prototype_decision_is_refused(self):
        self.assert_refused(self.check(SPEC.replace("Prototype: Not applicable", "Prototype:")), "Prototype")

    def test_scenario_no_task_covers_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("- Scenarios: S2\n", "")), "S2 is covered by no task")

    def test_scenario_two_tasks_cover_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("- Scenarios: S2", "- Scenarios: S1, S2")), "S1 is covered by 2 tasks")

    def test_requirement_no_task_covers_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("- Requirements: N1\n", "")), "N1 is covered by no task")

    def test_task_naming_a_scenario_the_spec_lacks_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("- Scenarios: S2", "- Scenarios: S2, S9")), "S9")

    def test_task_in_the_table_without_a_section_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("## T2. Print the invoice", "## Print the invoice")), "T2")

    def test_unknown_task_status_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("| T1 | todo |", "| T1 | waiting |")), "waiting")

    def test_dependency_on_a_missing_task_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("| T1 | todo |", "| T7 | todo |")), "T7")

    def test_task_started_before_its_dependency_is_done_is_refused(self):
        plan = PLAN.replace("| - | done |", "| - | todo |").replace("| T1 | todo |", "| T1 | in-progress |")

        self.assert_refused(self.check(plan=plan), "T2 is in-progress but T1 is todo")

    def test_tasks_depending_on_each_other_are_refused(self):
        plan = PLAN.replace("| Place the order | - | done |", "| Place the order | T2 | todo |")

        self.assert_refused(self.check(plan=plan), "depend on each other")

    def test_task_without_files_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("- Files: src/invoice.py\n", "")), "T2 has no Files")

    def test_task_with_an_unknown_model_is_refused(self):
        self.assert_refused(self.check(plan=PLAN.replace("- Model: small", "- Model: tiny")), "Model")

    def test_only_the_given_spec_folders_are_checked(self):
        other = self.project / "docs/specs/2025-01-01-old"
        other.mkdir(parents=True)
        (other / "SPEC.md").write_text("# Old\n\n- Status: Whatever\n")

        result = self.check(SPEC, PLAN, "docs/specs/2026-01-10-place-order/PLAN.md")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_refused(self.check(), "2025-01-01-old")


class AgentRulesTest(unittest.TestCase):
    BLOCKED = 2

    def run_as(self, agent, command):
        call = {"tool_name": "Bash", "tool_input": {"command": command}}
        if agent:
            call["agent_type"] = agent

        return subprocess.run([sys.executable, str(AGENT_RULES)], input=json.dumps(call), capture_output=True, text=True)

    def assert_blocked(self, agent, command, reason):
        result = self.run_as(agent, command)
        self.assertEqual(result.returncode, self.BLOCKED, f"{command}: {result.stderr}")
        self.assertIn(reason, result.stderr)

    def assert_allowed(self, agent, command):
        result = self.run_as(agent, command)
        self.assertEqual(result.returncode, 0, f"{command}: {result.stderr}")

    def test_main_session_is_not_restricted(self):
        self.assert_allowed(None, "git push origin main")

    def test_unknown_agent_is_not_restricted(self):
        self.assert_allowed("Explore", "rm -rf build")

    def test_reviewer_may_read_history(self):
        for command in (
            "git diff abc123..HEAD",
            "git --no-pager log --oneline -20 | head -5",
            "git -C .worktrees/T1 show HEAD:src/app.py",
            "git diff $(git merge-base HEAD main)..HEAD -- src 2>/dev/null",
            "git branch --show-current && git status --short",
            "git log --format='%an <%ae>' -1",
        ):
            self.assert_allowed("rs-code-reviewer", command)

    def test_reviewer_may_not_change_the_repository(self):
        for command in ("git commit -am x", "git checkout main", "git reset --hard HEAD~1", "git branch -D feat", "git stash"):
            self.assert_blocked("rs-code-reviewer", command, "read-only git")

    def test_reviewer_may_not_run_other_programs(self):
        for command in ("rm -rf src", "python fix.py", "git log | sh", "npm test"):
            self.assert_blocked("rs-code-reviewer", command, "read-only git")

    def test_reviewer_may_not_write_files_from_git_output(self):
        self.assert_blocked("rs-code-reviewer", "git diff > src/app.py", "read-only git")
        self.assert_blocked("rs-code-reviewer", "git diff --output=src/app.py", "read-only git")

    def test_reviewer_may_not_hide_a_command_inside_another(self):
        self.assert_blocked("rs-code-reviewer", "git diff $(rm -rf src)", "read-only git")

    def test_reviewer_from_a_plugin_is_held_to_the_same_rules(self):
        self.assert_blocked("development:rs-code-reviewer", "git commit -am x", "read-only git")

    def test_verifier_may_run_the_app_and_read_history(self):
        for command in ("npm run dev &", "dotnet test --filter S1", "git log -1", "npx playwright screenshot http://localhost:5000 evidence/verify-S1.png"):
            self.assert_allowed("rs-verifier", command)

    def test_verifier_may_not_change_the_repository(self):
        for command in ("git commit -am x", "git add -A && git push", "git checkout -- src"):
            self.assert_blocked("rs-verifier", command, "git")

    def test_gate_runner_may_run_the_gate_but_not_change_the_repository(self):
        self.assert_allowed("rs-gate-runner", ".githooks/validate all")
        self.assert_blocked("rs-gate-runner", "git stash && dotnet test", "git")

    def test_implementer_may_commit_but_not_push(self):
        self.assert_allowed("rs-task-implementer", "git add -A && git commit -m x")
        self.assert_blocked("rs-task-implementer", "git commit -m x && git push origin feat", "push")

    def test_push_named_in_a_commit_message_is_allowed(self):
        self.assert_allowed("rs-task-implementer", "git commit -F - <<'EOF'\nExplain git push\nEOF")


if __name__ == "__main__":
    unittest.main()
