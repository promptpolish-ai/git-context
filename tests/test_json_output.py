import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def run(cmd, cwd, **kwargs):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True, **kwargs)


class JsonOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmpdir.name)
        run(["git", "init"], self.repo)
        run(["git", "config", "user.email", "test@example.com"], self.repo)
        run(["git", "config", "user.name", "Test User"], self.repo)
        (self.repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        run(["git", "add", "."], self.repo)
        run(["git", "commit", "-m", "initial"], self.repo)

    def tearDown(self):
        self.tmpdir.cleanup()

    def git_context(self, *args):
        return run([sys.executable, str(REPO / "git-context"), "--dir", str(self.repo), *args], REPO)

    def test_json_output_is_valid_and_structured(self):
        result = self.git_context("--json", "--log", "1")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["repository"], self.repo.name)
        self.assertEqual(payload["path"], str(self.repo))
        self.assertIn(payload["git"]["branch"], {"main", "master"})
        self.assertTrue(payload["git"]["working_tree_clean"])
        self.assertEqual(payload["git"]["unstaged_changes"], [])
        self.assertEqual(payload["git"]["staged_changes"], [])
        self.assertEqual(len(payload["recent_commits"]), 1)
        self.assertIsInstance(payload["branches"], list)
        self.assertIsInstance(payload["project_structure"], list)
        self.assertNotIn("files", payload)

    def test_json_files_are_structured_when_requested(self):
        result = self.git_context("--json", "--files", "--log", "0")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["recent_commits"], [])
        self.assertIn("files", payload)
        paths = {item["path"] for item in payload["files"]}
        self.assertIn("README.md", paths)
        self.assertIn("src/app.py", paths)
        for item in payload["files"]:
            self.assertLessEqual({"path", "language", "size", "content", "truncated"}, set(item))

    def test_json_output_option_writes_file(self):
        output_path = self.repo / "context.json"
        result = self.git_context("--json", "--output", str(output_path))

        self.assertIn("Written to", result.stdout)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["repository"], self.repo.name)

    def test_markdown_output_still_works(self):
        result = self.git_context("--log", "0")

        self.assertIn("# git-context:", result.stdout)
        self.assertIn("## Project Structure", result.stdout)


if __name__ == "__main__":
    unittest.main()
