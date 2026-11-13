"""Tests for bin/harness and the validation hook. Standard library only."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VALIDATE = REPO / "plugins" / "validation" / "githooks" / "validate"

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


if __name__ == "__main__":
    unittest.main()
