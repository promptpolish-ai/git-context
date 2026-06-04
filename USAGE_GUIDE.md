# Usage Guide

## Basic usage

Run `git-context` from inside a git repository:

```bash
git-context
```

This prints a human-readable summary of the current repository state, including branch, status, recent commits, and diffs.

## JSON mode

For scripts and tooling, use JSON output:

```bash
git-context --json
```

Example shape:

```json
{
  "repository": "my-repo",
  "root": "/path/to/my-repo",
  "branch": "main",
  "status": "M README.md",
  "untracked_files": ["notes.txt"],
  "staged_diff": "diff --git a/file.txt b/file.txt ...",
  "unstaged_diff": "diff --git a/README.md b/README.md ...",
  "recent_commits": [
    {
      "hash": "abc123...",
      "author": "Jane Doe",
      "date": "2024-01-01 12:00:00 +0000",
      "subject": "Add feature"
    }
  ]
}
```

## Limit commits

```bash
git-context --commits 5
```

## Combining flags

```bash
git-context --commits 3 --json
```
