# git-context

A simple CLI tool to collect git context (branch, commit, diff, etc.) for AI prompts.

## Installation

```bash
pip install git-context
```

Or install from source:

```bash
pip install .
```

## Usage

```bash
git-context
```

This will output something like:

```
=== Git Context ===
Branch: main
Commit: a1b2c3d4e5f6...
Message: Fix bug in parser
Remote: https://github.com/user/repo.git
Changed files: src/main.py, tests/test_main.py

--- Diff ---
diff --git a/src/main.py b/src/main.py
...
```

### JSON Output

Use the `--json` flag to get the output in JSON format:

```bash
git-context --json
```

Example JSON output:

```json
{
  "branch": "main",
  "commit_hash": "a1b2c3d4e5f6...",
  "commit_message": "Fix bug in parser",
  "diff": "diff --git a/src/main.py b/src/main.py\n...",
  "changed_files": ["src/main.py", "tests/test_main.py"],
  "remote_url": "https://github.com/user/repo.git"
}
```

## Requirements

- Python 3.7+
- Git installed and accessible from command line

## License

MIT
