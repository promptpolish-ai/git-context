# git-context

`git-context` prints the current repository context so it can be pasted into prompts, scripts, or automation.

## Installation

See `SETUP.md` for installation instructions.

## Usage

```bash
git-context
```

Output the same context as JSON:

```bash
git-context --json
```

Limit the number of recent commits:

```bash
git-context --commits 5
```

## JSON output

Use `--json` when you want machine-readable output for shell scripts, editor integrations, or other tools. The JSON output contains the same core fields as the text mode, including repository metadata, status, diffs, untracked files, and recent commits.

## More docs

- `USAGE_GUIDE.md`
- `SETUP.md`
- `RELEASE_NOTES.md`
