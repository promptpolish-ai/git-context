#!/usr/bin/env python3
"""
git-context — Generate AI-friendly context for any git repo.
Dump project structure, git log, file contents, and branch topology
in one optimized prompt-ready block.

Usage:  git context [--depth N] [--files] [--log N] [--output file] [--dir <path>] [--json]
"""

import argparse
import json
import os
import subprocess
import sys
import fnmatch
from pathlib import Path
from datetime import datetime

DEFAULT_IGNORE = {
    '.git', 'node_modules', '.next', 'dist', 'build', 'target',
    '__pycache__', '.cache', 'venv', '.venv', '.env', 'env',
    '.tox', '.eggs', '*.egg-info', '.pytest_cache', '.mypy_cache',
    '.DS_Store', '.idea', '.vscode', '*.swp', '*.swo', '*~',
    '*.pyc', '*.pyo', '.coverage', 'coverage', '*.log',
    '.terraform', 'vendor', '.bundle',
}

def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or os.getcwd(), timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""

def size_fmt(n):
    if n > 1_000_000: return f"{n/1_000_000:.1f}MB"
    if n > 1_000: return f"{n/1_000:.0f}KB"
    return f"{n}B"

def should_ignore(name, ignored):
    for pat in ignored:
        if pat.startswith('*'):
            if name.endswith(pat[1:]): return True
        elif fnmatch.fnmatch(name, pat): return True
    return False

def tree(path, prefix="", ignored=DEFAULT_IGNORE, depth=3, current_depth=0):
    if current_depth > depth:
        return ""
    items = []
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return ""
    for e in entries:
        fp = os.path.join(path, e)
        if e.startswith('.') or should_ignore(e, ignored):
            continue
        is_dir = os.path.isdir(fp)
        items.append((e, fp, is_dir))
    result = ""
    for i, (name, fp, is_dir) in enumerate(items):
        is_last = i == len(items) - 1
        conn = "└── " if is_last else "├── "
        result += f"{prefix}{conn}{name}/\n" if is_dir else f"{prefix}{conn}{name}  ({size_fmt(os.path.getsize(fp))})\n"
        if is_dir:
            deeper = "    " if is_last else "│   "
            result += tree(fp, prefix + deeper, ignored, depth, current_depth + 1)
    return result

def tree_dict(path, ignored=DEFAULT_IGNORE, depth=3, current_depth=0):
    """Build tree as a dict structure for JSON output."""
    if current_depth > depth:
        return {}
    items = {}
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return {}
    for e in entries:
        fp = os.path.join(path, e)
        if e.startswith('.') or should_ignore(e, ignored):
            continue
        is_dir = os.path.isdir(fp)
        if is_dir:
            items[e + "/"] = tree_dict(fp, ignored, depth, current_depth + 1)
        else:
            try:
                size = os.path.getsize(fp)
            except OSError:
                size = 0
            items[e] = {"size": size, "size_human": size_fmt(size)}
    return items

def file_contents(path, ignored=DEFAULT_IGNORE, max_total=15000):
    ext_map = {
        '.py': 'py', '.js': 'js', '.ts': 'ts', '.tsx': 'tsx', '.jsx': 'jsx',
        '.go': 'go', '.rs': 'rs', '.rb': 'rb', '.java': 'java', '.kt': 'kt',
        '.swift': 'swift', '.c': 'c', '.h': 'h', '.cpp': 'cpp', '.hpp': 'hpp',
        '.cs': 'cs', '.php': 'php', '.vue': 'vue', '.svelte': 'svelte',
        '.css': 'css', '.scss': 'scss', '.html': 'html', '.xml': 'xml',
        '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
        '.md': 'md', '.txt': 'txt', '.sh': 'sh', '.bash': 'sh', '.zsh': 'sh',
        '.sql': 'sql', '.graphql': 'graphql', '.proto': 'proto',
        '.dockerfile': 'dockerfile', '.tf': 'tf', '.env': 'env',
        '.conf': 'conf', '.ini': 'ini', '.cfg': 'cfg',
    }
    snippet_exts = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.rb',
                    '.java', '.kt', '.swift', '.c', '.h', '.cpp', '.cs', '.php',
                    '.vue', '.svelte', '.css', '.scss', '.html', '.xml',
                    '.json', '.yaml', '.yml', '.toml', '.md', '.sh', '.bash',
                    '.zsh', '.sql', '.graphql', '.proto', '.tf', '.conf', '.ini'}
    
    result = ""
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ignored and d != 'node_modules']
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if f.endswith('.min.js') or f.endswith('.min.css'):
                continue
            if ext not in snippet_exts:
                continue
            fp = os.path.join(root, f)
            try:
                content = Path(fp).read_text(encoding='utf-8', errors='replace')
                rel = os.path.relpath(fp, path)
                block = f"\n--- {rel} ---\n```{ext_map.get(ext, '')}\n{content.strip()}\n```\n"
                if total + len(block) > max_total:
                    remaining = max_total - total
                    result += block[:remaining] + f"\n... (truncated, more files in {rel})"
                    total = max_total
                    break
                result += block
                total += len(block)
            except Exception:
                continue
        if total >= max_total:
            break
    return result

def file_contents_dict(path, ignored=DEFAULT_IGNORE, max_total=15000):
    """Collect file contents as dict for JSON output."""
    snippet_exts = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.rb',
                    '.java', '.kt', '.swift', '.c', '.h', '.cpp', '.cs', '.php',
                    '.vue', '.svelte', '.css', '.scss', '.html', '.xml',
                    '.json', '.yaml', '.yml', '.toml', '.md', '.sh', '.bash',
                    '.zsh', '.sql', '.graphql', '.proto', '.tf', '.conf', '.ini'}
    
    files_dict = {}
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ignored and d != 'node_modules']
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if f.endswith('.min.js') or f.endswith('.min.css'):
                continue
            if ext not in snippet_exts:
                continue
            fp = os.path.join(root, f)
            try:
                content = Path(fp).read_text(encoding='utf-8', errors='replace')
                rel = os.path.relpath(fp, path)
                block_size = len(content)
                if total + block_size > max_total:
                    remaining = max_total - total
                    files_dict[rel] = content[:remaining] + f"\n... (truncated)"
                    total = max_total
                    break
                files_dict[rel] = content
                total += block_size
            except Exception:
                continue
        if total >= max_total:
            break
    return files_dict

def fmt_timestamp(ts):
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return ts[:19]

def parse_commit(line):
    """Parse a git log line into structured data."""
    # Format: "hash (refs) message (author, time)"
    parts = line.split(" ", 1)
    if len(parts) < 2:
        return {"hash": line, "message": "", "refs": "", "author": "", "date": ""}
    
    hash_val = parts[0]
    rest = parts[1]
    
    # Extract refs if present
    refs = ""
    if rest.startswith("("):
        idx = rest.find(")")
        if idx > 0:
            refs = rest[1:idx]
            rest = rest[idx+1:].strip()
    
    # Extract author and date from the end
    author = ""
    date = ""
    if "(" in rest and rest.endswith(")"):
        last_paren = rest.rfind("(")
        if last_paren > 0:
            meta = rest[last_paren+1:-1]
            rest = rest[:last_paren].strip()
            if ", " in meta:
                author, date = meta.rsplit(", ", 1)
            else:
                author = meta
    
    return {
        "hash": hash_val,
        "refs": refs,
        "message": rest.strip(),
        "author": author,
        "date": date
    }

def main():
    p = argparse.ArgumentParser(description='Generate AI-friendly context for a git repo')
    p.add_argument('--depth', type=int, default=4, help='Directory tree depth (default: 4)')
    p.add_argument('--files', action='store_true', help='Include source file contents')
    p.add_argument('--log', type=int, default=20, help='Number of recent commits (default: 20, 0=skip)')
    p.add_argument('--output', '-o', help='Write to file instead of stdout')
    p.add_argument('--dir', default=os.getcwd(), help='Target directory (default: cwd)')
    p.add_argument('--json', action='store_true', help='Output in JSON format')
    args = p.parse_args()

    target = os.path.abspath(args.dir)
    if not os.path.isdir(os.path.join(target, '.git')):
        print(f"❌ Not a git repo: {target}", file=sys.stderr)
        sys.exit(1)

    repo_name = os.path.basename(target)
    
    # Collect data
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], target)
    remote = run(["git", "remote", "get-url", "origin"], target)
    
    has_unstaged = run(["git", "diff", "--stat"], target)
    has_staged = run(["git", "diff", "--cached", "--stat"], target)
    
    status_info = {
        "clean": not has_unstaged and not has_staged,
        "unstaged_changes": has_unstaged.split(chr(10))[-1] if has_unstaged else None,
        "staged_changes": has_staged.split(chr(10))[-1] if has_staged else None,
    }
    
    # Recent commits
    commits = []
    if args.log > 0:
        log = run(["git", "log", f"--max-count={args.log}", "--oneline", "--graph",
                    "--pretty=format:%h %d %s (%an, %ar)"], target)
        if log:
            for line in log.split(chr(10)):
                line = line.strip()
                if line:
                    # Remove graph characters
                    clean = line.lstrip("* |\\/ ")
                    if clean:
                        commits.append(parse_commit(clean))
    
    # Branches
    branches_raw = run(["git", "branch", "-a"], target)
    branches = [b.strip().lstrip("* ") for b in branches_raw.split(chr(10)) if b.strip()] if branches_raw else []
    
    # Tree
    tree_data = tree_dict(target, ignored=DEFAULT_IGNORE, depth=args.depth)
    
    # File contents
    files = {}
    if args.files:
        files = file_contents_dict(target)
    
    # Generate output
    if args.json:
        output_data = {
            "repo": repo_name,
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "path": target,
            "git": {
                "branch": branch,
                "remote": remote,
                "status": status_info,
            },
            "commits": commits,
            "branches": branches,
            "tree": tree_data,
        }
        if args.files:
            output_data["files"] = files
        
        output = json.dumps(output_data, indent=2, ensure_ascii=False)
    else:
        # Original text output
        sections = []
        sections.append(f"# git-context: {repo_name}")
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append(f"Path: {target}")
        sections.append("")

        # Git info
        sections.append(f"## Git Info\n- Branch: `{branch}`")
        sections.append(f"- Remote: {remote}")
        
        status = ""
        if has_unstaged: status += f"\n- Unstaged changes: {has_unstaged.split(chr(10))[-1]}"
        if has_staged: status += f"\n- Staged changes: {has_staged.split(chr(10))[-1]}"
        if not has_unstaged and not has_staged:
            status += "\n- Working tree: clean"
        sections.append(status)

        # Recent commits
        if commits:
            log_display = run(["git", "log", f"--max-count={args.log}", "--oneline", "--graph",
                        "--pretty=format:%h %d %s (%an, %ar)"], target)
            sections.append(f"\n## Recent Commits (last {args.log})")
            sections.append(f"```\n{log_display}\n```")

        # Branch topology
        if branches_raw:
            sections.append("\n## Branches")
            sections.append(f"```\n{branches_raw}\n```")

        # Directory tree
        tree_out = tree(target, ignored=DEFAULT_IGNORE, depth=args.depth)
        sections.append(f"\n## Project Structure (depth={args.depth})")
        sections.append(f"```\n{tree_out}\n```")

        # File contents
        if args.files:
            contents = file_contents(target)
            if contents:
                sections.append("\n## File Contents")
                sections.append(contents)

        output = "\n".join(sections)
    
    if args.output:
        Path(args.output).write_text(output)
        print(f"✅ Written to {args.output}")
    else:
        print(output)

if __name__ == '__main__':
    main()
