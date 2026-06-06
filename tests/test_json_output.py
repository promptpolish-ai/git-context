import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)


class JsonOutputTest(unittest.TestCase):
    def test_json_flag_outputs_parseable_repo_context(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")
            (repo / "README.md").write_text("hello", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "feat: initial commit")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "git_context",
                    "--dir",
                    str(repo),
                    "--json",
                    "--log",
                    "1",
                    "--depth",
                    "1",
                ],
                cwd=PROJECT_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["repo"], repo.name)
            self.assertTrue(payload["git"]["branch"])
            self.assertTrue(payload["git"]["status"]["clean"])
            self.assertIn("feat: initial commit", payload["recent_commits"][0])
            self.assertIn("README.md", payload["project_structure"])


if __name__ == "__main__":
    unittest.main()
