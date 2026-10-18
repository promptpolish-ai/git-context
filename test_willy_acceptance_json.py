"""Operator acceptance checks for issue #2; not upstream tests or payout proof.

No required JSON schema has been confirmed by the maintainer. These checks only
cover a structured, parseable result and regression of the existing CLI modes.
All subprocesses and fixture writes run inside Willi's offline test sandbox.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class JsonOutputAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "Grüße repo"
        self.repo.mkdir()
        self.marker = 'WILLY_FIXTURE_ß "quoted" \\ slash'
        (self.repo / "sample.py").write_text(self.marker, encoding="utf-8")
        for args in (["init", "-q"], ["add", "sample.py"],
                     ["-c", "user.name=Offline Fixture", "-c", "user.email=fixture@example.invalid",
                      "commit", "-q", "-m", "offline fixture"]):
            subprocess.run(["/usr/bin/git", "-C", str(self.repo), *args], check=True, capture_output=True, timeout=5)
        self.source_root = Path(__file__).resolve().parent
        self.commands = [
            [sys.executable, "-I", str(self.source_root / "git-context")],
            [sys.executable, "-I", "-c", f"import sys;sys.path.insert(0,{str(self.source_root)!r});from git_context import main;main()"],
        ]

    def run_cli(self, command, *args):
        return subprocess.run([*command, "--dir", str(self.repo), *args], cwd=self.source_root,
                              capture_output=True, text=True, encoding="utf-8", timeout=10)

    def parsed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIsInstance(value, (dict, list))
        self.assertTrue(value)
        return value

    def test_default_text_mode(self):
        for command in self.commands:
            with self.subTest(command=command):
                result = self.run_cli(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.startswith("# git-context:"))

    def test_json_stdout(self):
        for command in self.commands:
            with self.subTest(command=command):
                self.parsed(self.run_cli(command, "--json"))

    def test_json_files_and_unicode(self):
        for command in self.commands:
            with self.subTest(command=command):
                value = self.parsed(self.run_cli(command, "--json", "--files"))
                self.assertIn("WILLY_FIXTURE_ß", json.dumps(value, ensure_ascii=False))

    def test_json_without_log(self):
        for command in self.commands:
            with self.subTest(command=command):
                self.parsed(self.run_cli(command, "--json", "--log", "0"))

    def test_json_output_file_has_no_stdout_noise(self):
        for index, command in enumerate(self.commands):
            with self.subTest(command=command):
                output = Path(self.temp.name) / f"output-{index}.json"
                result = self.run_cli(command, "--json", "--files", "-o", str(output))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIsInstance(json.loads(output.read_text(encoding="utf-8")), (dict, list))

    def test_text_output_file_remains_compatible(self):
        for index, command in enumerate(self.commands):
            with self.subTest(command=command):
                output = Path(self.temp.name) / f"output-{index}.md"
                result = self.run_cli(command, "-o", str(output))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(output.read_text(encoding="utf-8").startswith("# git-context:"))

    def test_invalid_directory_still_fails(self):
        for command in self.commands:
            with self.subTest(command=command):
                result = self.run_cli(command, "--json", "--dir", str(Path(self.temp.name) / "absent"))
                self.assertNotEqual(result.returncode, 0)

    def test_help_advertises_flag(self):
        for command in self.commands:
            with self.subTest(command=command):
                result = self.run_cli(command, "--help")
                self.assertEqual(result.returncode, 0)
                self.assertIn("--json", result.stdout)
