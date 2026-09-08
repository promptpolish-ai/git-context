import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = ([sys.executable, str(ROOT / 'git-context')],
               [sys.executable, '-m', 'git_context'])


class JsonOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'example'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test Author')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.repo / 'hello.py').write_text('print("café \\\"hello\\\"")\n', encoding='utf-8')
        self.git('add', 'hello.py')
        self.git('commit', '-qm', 'Initial café example')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True,
                              capture_output=True, text=True)

    def cli(self, entrypoint, *args):
        return subprocess.run([*entrypoint, '--dir', str(self.repo), *args],
                              cwd=ROOT, capture_output=True, text=True, encoding='utf-8')

    def test_structured_stdout_and_default_markdown(self):
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                result = self.cli(entry, '--json')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                data = json.loads(result.stdout)
                self.assertEqual(data['repo_name'], 'example')
                self.assertEqual(data['path'], str(self.repo))
                self.assertEqual(data['git_info']['branch'], self.git('branch', '--show-current').stdout.strip())
                self.assertEqual(data['git_info']['remote'], '')
                self.assertIn('Initial café example', data['recent_commits'])
                self.assertIsInstance(data['branches'], list)
                self.assertIn('hello.py', data['project_structure'])
                self.assertNotIn('file_contents', data)
                markdown = self.cli(entry).stdout
                self.assertTrue(markdown.startswith('# git-context: example\n'))
                self.assertIn('## Recent Commits', markdown)

    def test_files_depth_and_disabled_log(self):
        folder = self.repo / 'nested'
        folder.mkdir()
        (folder / 'child.py').write_text('pass\n')
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                result = self.cli(entry, '--json', '--files', '--log', '0', '--depth', '0')
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data['recent_commits'], '')
                self.assertIn('café', data['file_contents'])
                self.assertIn('nested/', data['project_structure'])
                self.assertNotIn('child.py', data['project_structure'])

    def test_file_output_and_changed_files(self):
        (self.repo / 'hello.py').write_text('print("changed")\n')
        (self.repo / 'new.py').write_text('pass\n')
        self.git('add', 'new.py')
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                output = Path(self.temp.name) / 'context.json'
                result = self.cli(entry, '--json', '-o', str(output))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertIn('Written to', result.stderr)
                data = json.loads(output.read_text(encoding='utf-8'))
                self.assertIn('hello.py', data['git_info']['unstaged_changes'])
                self.assertIn('new.py', data['git_info']['staged_changes'])

    def test_empty_repo_and_invalid_directory(self):
        empty = Path(self.temp.name) / 'empty'
        empty.mkdir()
        subprocess.run(['git', 'init', '-q', str(empty)], check=True)
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                result = self.cli(entry, '--dir', str(empty), '--json', '--files')
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data['recent_commits'], '')
                self.assertEqual(data['branches'], [])
                self.assertEqual(data['file_contents'], '')
                invalid = self.cli(entry, '--dir', self.temp.name, '--json')
                self.assertEqual(invalid.returncode, 1)
                self.assertEqual(invalid.stdout, '')
                self.assertIn('Not a git repo', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
