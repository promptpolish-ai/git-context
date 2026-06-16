#!/usr/bin/env python3
"""
git-context — Generate AI-friendly context for any git repo.
Dump project structure, git log, file contents, and branch topology
in one optimized prompt-ready block.

Usage:  git context [--depth N] [--files] [--log N] [--output file] [--dir <path>] [--json]
"""

import argparse
import os
import subprocess
import sys
import fnmatch
import json
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

def fmt_timestamp(ts):
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return ts[:19]

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
    git_info = {
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"], target),
        "remote": run(["git", "remote", "get-url", "origin"], target),
    }
    
    has_unstaged = run(["git", "diff", "--stat"], target)
    has_staged = run(["git", "diff", "--cached", "--stat"], target)
    status_msg = ""
    if has_unstaged: status_msg += f"Unstaged changes: {has_unstaged.split(chr(10))[-1]} "
    if has_staged: status_msg += f"Staged changes: {has_staged.split(chr(10))[-1]} "
    if not has_unstaged and not has_staged:
        status_msg = "Working tree: clean"
    
    git_info["status"] = status_msg.strip()
    
    log_data = []
    if args.log > 0:
        raw_log = run(["git", "log", f"--max-count={args.log}", "--oneline", "--graph",
                        "--pretty=format:%h %d %s (%an, %ar)"], target)
        if raw_log:
            log_data = raw_log.splitlines()
    
    branches_data = run(["git", "branch", "-a"], target)
    
    tree_out = tree(target, ignored=DEFAULT_IGNORE, depth=args.depth)
    
    contents_data = ""
    if args.files:
        contents_data = file_contents(target)

    # Output logic
    if args.json:
        data = {
            "repo_name": repo_name,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "path": target,
            "git_info": git_info,
            "recent_commits": log_data,
            "branches": branches_data,
            "project_structure": tree_out,
            "file_contents": contents_data
        }
        output = json.dumps(data, indent=2)
    else:
        sections = [
            f"# git-context: {repo_name}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Path: {target}",
            "",
            f"## Git Info\n- Branch: `{git_info['branch']}`",
            f"- Remote: {git_info['remote']}",
            f"Status: {git_info['status']}",
            "",
        ]
        if log_data:
            sections.append(f"## Recent Commits (last {args.log})")
            sections.append(f"```\n{''.join(log_data)}\n```")
        if branches_data:
            sections.append(f"\n## Branches")
            sections.append(f"```\n{branches_data}\n```")
        sections.append(f"\n## Project Structure (depth={args.depth})")
        sections.append(f"```\n{tree_out}\n```")
        if contents_data:
            sections.append("\n## File Contents")
            sections.append(contents_data)
        output = "\n".join(sections)
    
    if args.output:
        Path(args.output).write_text(output)
        print(f"✅ Written to {args.output}")
    else:
        print(output)

if __name__ == '__main__':
    main()
