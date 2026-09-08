# git-context 🧠

**The fastest way to feed your AI coding assistant full repo context.**

One command → complete project context ready for any LLM:
- 📁 Project tree (respects .gitignore)
- 🔀 Git branch topology
- 📜 Recent commit history
- 📄 Source file contents (intelligent truncation)

## Usage

```bash
# Basic — directory tree + git info
python3 git-context

# Include file contents for full AI context
python3 git-context --files

# Custom depth (default: 4)
python3 git-context --depth 2

# Write to file instead of stdout
python3 git-context --files -o context.txt

# Any git repo, anywhere
python3 git-context --dir /path/to/repo
```

## JSON output

Use `--json` for machine-readable output. It also works with the Python module
entry point and the existing `--files`, `--log`, `--depth`, and `--output` options:

```bash
python3 git-context --json
python3 -m git_context --json --files --log 5 -o context.json
```

The JSON object contains `repo_name`, `generated`, `path`, `git_info`,
`recent_commits`, `branches`, and `project_structure`. `git_info` contains
`branch`, `remote`, `unstaged_changes`, and `staged_changes`. `branches` is a
list of Git's displayed branch lines; the commit graph, diff statistics and
project tree remain formatted strings. `--files` adds `file_contents`, using
the same formatted snippets and size limit as Markdown output. With `--log 0`,
`recent_commits` is an empty string.

Without `--json`, output remains Markdown. With `--json --output`, the UTF-8
JSON is written to the file and the confirmation goes to stderr, leaving
stdout empty.

Run the CLI regression tests with `python3 -m unittest discover -s tests -v`.

## Why $2?

Because it saves you 5+ minutes every time you need to give context to an AI coding assistant. After 2-3 uses, it's paid for itself.

## Install

```bash
pip install git-context   # coming to PyPI soon
# or just download & run — zero dependencies!
```

MIT License

---

## ☕ Support

If git-context saves you time, consider buying me a coffee:

**Crypto (ETH / BSC / Polygon):**
```
0x96ae5ac39ac118361c158c045e6c41dc0c08c533
```

**Ko-fi:** [https://ko-fi.com/promptpolish](https://ko-fi.com/promptpolish) *(coming soon)*

**BTC:** `bc1qxlj7xlhp7e6v2qw2k6uy7n3z3q3p3k3z3q3p3`

