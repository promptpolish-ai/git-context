import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from git_context import build_context


class JsonOutputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "README.md").write_text("# demo\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_context_is_json_serializable(self):
        args = argparse.Namespace(depth=1, files=True, log=0)

        context = build_context(str(self.repo), args)
        payload = json.loads(json.dumps(context))

        self.assertEqual(payload["repo"], self.repo.name)
        self.assertEqual(payload["project_structure"]["depth"], 1)
        self.assertIn("README.md", payload["project_structure"]["tree"])
        self.assertIn("--- README.md ---", payload["file_contents"])
        self.assertIn("git", payload)

    def test_module_json_flag_emits_valid_json(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "git_context",
                "--dir",
                str(self.repo),
                "--json",
                "--log",
                "0",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)

        self.assertEqual(payload["repo"], self.repo.name)
        self.assertEqual(payload["git"]["recent_commits"], "")
        self.assertIn("project_structure", payload)


if __name__ == "__main__":
    unittest.main()
