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

### JSON output

Use `python3 git-context --json` (or `python3 -m git_context --json`) for a
JSON object containing `repo_name`, `generated`, `path`, `git`, `recent_commits`,
`branches` and `project_structure`. Each commit has a hash, author, ISO date
and subject. The `git` object includes the current branch, remote and separate
staged/unstaged diff summaries. The project tree remains a formatted string.

`--json --files` also includes `file_contents`, using the existing formatted
snippets and truncation limit. `--depth` and `--log` still apply; `--log 0`
produces an empty commit list. To save UTF-8 JSON, use
`python3 git-context --json --files -o context.json`. Without `--json`, the
existing text output is retained. Invalid targets still report errors on stderr
and exit with status 1.

Run the integration tests with `python3 -m unittest discover -s tests -v`.
They require Git, but no Python dependencies.

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

