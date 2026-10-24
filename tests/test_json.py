"""Real Git/CLI integration checks; no third-party packages required."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class JsonOutputTests(unittest.TestCase):
    entrypoint = "script"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="git-context-test-")
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / "sample"
        self.target.mkdir()
        self.env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture Author")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        (self.target / "hello.py").write_text("print('hello')\n", encoding="utf-8")
        (self.target / "nested").mkdir()
        (self.target / "nested" / "unicode.md").write_text("café\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "Initial café")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.target, env=self.env,
                              encoding="utf-8", capture_output=True, check=True,
                              timeout=15).stdout.strip()

    def cli(self, *args):
        entry = [str(ROOT / "git-context")] if self.entrypoint == "script" else ["-m", "git_context"]
        return subprocess.run([sys.executable, "-B", *entry, "--dir", str(self.target), *args],
                              cwd=ROOT, env=self.env, encoding="utf-8",
                              capture_output=True, timeout=30)

    def context(self, *args):
        result = self.cli("--json", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_json_contains_real_repository_data(self):
        data = self.context()
        self.assertEqual(data["repo_name"], "sample")
        self.assertEqual(data["path"], str(self.target))
        self.assertEqual(data["git"]["branch"], "main")
        self.assertEqual(data["git"]["remote"], "")
        self.assertEqual(data["git"]["staged_diff"], "")
        self.assertEqual(data["git"]["unstaged_diff"], "")
        self.assertEqual(data["branches"], ["main"])
        self.assertEqual(data["recent_commits"][0]["hash"], self.git("rev-parse", "HEAD"))
        self.assertEqual(data["recent_commits"][0]["subject"], "Initial café")
        self.assertEqual(data["recent_commits"][0]["author"], "Fixture Author")
        self.assertIn("hello.py", data["project_structure"])
        self.assertNotIn("file_contents", data)

    def test_files_and_depth_flags_work_with_json(self):
        data = self.context("--files", "--depth", "0")
        self.assertIn("print('hello')", data["file_contents"])
        self.assertIn("café", data["file_contents"])
        self.assertIn("nested/", data["project_structure"])
        self.assertNotIn("unicode.md", data["project_structure"])

    def test_output_file_is_utf8_json(self):
        destination = Path(self.temp.name) / "context.json"
        result = self.cli("--json", "--files", "-o", str(destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(destination.read_bytes().decode("utf-8"))
        self.assertIn("café", data["file_contents"])
        self.assertIn("Written to", result.stdout)
        self.assertNotIn('"repo_name"', result.stdout)

    def test_log_limit_and_zero(self):
        (self.target / "second.txt").write_text("second\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "Second")
        self.assertEqual([c["subject"] for c in self.context("--log", "1")["recent_commits"]], ["Second"])
        self.assertEqual(self.context("--log", "0")["recent_commits"], [])

    def test_empty_repository_has_empty_history(self):
        empty = Path(self.temp.name) / "empty"
        empty.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(empty)], env=self.env,
                       capture_output=True, check=True, timeout=15)
        data = self.context("--dir", str(empty))
        self.assertEqual(data["recent_commits"], [])
        self.assertEqual(data["branches"], [])
        self.assertEqual(data["project_structure"], "")

    def test_staged_and_unstaged_changes_are_distinct(self):
        (self.target / "staged.py").write_text("staged = True\n", encoding="utf-8")
        self.git("add", "staged.py")
        (self.target / "hello.py").write_text("print('changed')\n", encoding="utf-8")
        data = self.context()
        self.assertIn("staged.py", data["git"]["staged_diff"])
        self.assertIn("hello.py", data["git"]["unstaged_diff"])

    def test_default_text_mode_and_invalid_target(self):
        result = self.cli("--log", "0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("# git-context: sample\n"))
        self.assertIn("## Project Structure", result.stdout)
        invalid = self.cli("--json", "--dir", self.temp.name)
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(invalid.stdout, "")
        self.assertIn("Not a git repo", invalid.stderr)


class ModuleJsonOutputTests(JsonOutputTests):
    entrypoint = "module"


if __name__ == "__main__":
    unittest.main()
