import subprocess
import tempfile
import unittest
from pathlib import Path

from git_context import file_contents


class FileContentsIgnoreTests(unittest.TestCase):
    def test_file_contents_skips_hidden_and_default_ignored_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

            (repo / ".secrets.py").write_text("API_TOKEN = 'do-not-print'\n", encoding="utf-8")
            (repo / ".env").write_text("SECRET_TOKEN=do-not-print\n", encoding="utf-8")
            (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")

            contents = file_contents(str(repo))

        self.assertIn("--- app.py ---", contents)
        self.assertIn("print('hello')", contents)
        self.assertNotIn(".secrets.py", contents)
        self.assertNotIn("API_TOKEN", contents)
        self.assertNotIn(".env", contents)
        self.assertNotIn("SECRET_TOKEN", contents)


if __name__ == "__main__":
    unittest.main()
