#!/usr/bin/env python3
"""
git-context - Generate AI-friendly context for any git repo.
Dump project structure, git log, file contents, and branch topology
in one optimized prompt-ready block.

Usage:  git context [--depth N] [--files] [--log N] [--output file] [--dir <path>] [--json]
"""

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path

DEFAULT_IGNORE = {
    '.git', 'node_modules', '.next', 'dist', 'build', 'target',
    '__pycache__', '.cache', 'venv', '.venv', '.env', 'env',
    '.tox', '.eggs', '*.egg-info', '.pytest_cache', '.mypy_cache',
    '.DS_Store', '.idea', '.vscode', '*.swp', '*.swo', '*~',
    '*.pyc', '*.pyo', '.coverage', 'coverage', '*.log',
    '.terraform', 'vendor', '.bundle',
}

EXT_MAP = {
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

SNIPPET_EXTS = set(EXT_MAP)


def run(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def size_fmt(n):
    if n > 1_000_000:
        return f"{n / 1_000_000:.1f}MB"
    if n > 1_000:
        return f"{n / 1_000:.0f}KB"
    return f"{n}B"


def sanitize_remote(remote):
    if not remote:
        return remote
    try:
        parts = urlsplit(remote)
        if parts.username or parts.password:
            host = parts.hostname or ""
            if parts.port:
                host = f"{host}:{parts.port}"
            return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return remote


def should_ignore(name, ignored):
    for pat in ignored:
        if pat.startswith('*'):
            if name.endswith(pat[1:]):
                return True
        elif fnmatch.fnmatch(name, pat):
            return True
    return False


def tree(path, prefix="", ignored=DEFAULT_IGNORE, depth=3, current_depth=0):
    if current_depth > depth:
        return ""
    items = []
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return ""
    for entry in entries:
        fp = os.path.join(path, entry)
        if entry.startswith('.') or should_ignore(entry, ignored):
            continue
        items.append((entry, fp, os.path.isdir(fp)))

    result = ""
    for index, (name, fp, is_dir) in enumerate(items):
        is_last = index == len(items) - 1
        conn = "└── " if is_last else "├── "
        result += f"{prefix}{conn}{name}/\n" if is_dir else f"{prefix}{conn}{name}  ({size_fmt(os.path.getsize(fp))})\n"
        if is_dir:
            deeper = "    " if is_last else "│   "
            result += tree(fp, prefix + deeper, ignored, depth, current_depth + 1)
    return result


def project_structure(path, repo_root, ignored=DEFAULT_IGNORE, depth=3, current_depth=0):
    if current_depth > depth:
        return []
    entries = []
    try:
        names = sorted(os.listdir(path))
    except PermissionError:
        return entries

    for name in names:
        fp = os.path.join(path, name)
        if name.startswith('.') or should_ignore(name, ignored):
            continue
        is_dir = os.path.isdir(fp)
        entry = {
            "name": name,
            "type": "directory" if is_dir else "file",
            "path": os.path.relpath(fp, repo_root),
        }
        if is_dir:
            entry["children"] = project_structure(fp, repo_root, ignored, depth, current_depth + 1)
        else:
            entry["size_bytes"] = os.path.getsize(fp)
            entry["size"] = size_fmt(entry["size_bytes"])
        entries.append(entry)
    return entries


def collect_file_contents(path, ignored=DEFAULT_IGNORE, max_total=15000):
    files = []
    total = 0
    truncated = False
    truncated_at = None

    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not should_ignore(d, ignored) and d != 'node_modules']
        for filename in sorted(filenames):
            ext = os.path.splitext(filename)[1].lower()
            if filename.endswith('.min.js') or filename.endswith('.min.css') or ext not in SNIPPET_EXTS:
                continue
            fp = os.path.join(root, filename)
            try:
                content = Path(fp).read_text(encoding='utf-8', errors='replace').strip()
                rel = os.path.relpath(fp, path)
                block_len = len(content) + len(rel) + 40
                if total + block_len > max_total:
                    remaining = max_total - total
                    files.append({
                        "path": rel,
                        "language": EXT_MAP.get(ext, ""),
                        "content": content[:max(0, remaining)],
                        "truncated": True,
                    })
                    truncated = True
                    truncated_at = rel
                    total = max_total
                    break
                files.append({
                    "path": rel,
                    "language": EXT_MAP.get(ext, ""),
                    "content": content,
                    "truncated": False,
                })
                total += block_len
            except Exception:
                continue
        if total >= max_total:
            break

    return {
        "files": files,
        "truncated": truncated,
        "truncated_at": truncated_at,
        "max_total_chars": max_total,
    }


def file_contents(path, ignored=DEFAULT_IGNORE, max_total=15000):
    collected = collect_file_contents(path, ignored, max_total)
    result = ""
    for item in collected["files"]:
        result += f"\n--- {item['path']} ---\n```{item['language']}\n{item['content']}\n```\n"
        if item["truncated"]:
            result += f"\n... (truncated, more files in {item['path']})"
    return result


def collect_context(target, depth=4, log_count=20, include_files=False):
    repo_name = os.path.basename(target)
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], target)
    remote = run(["git", "remote", "get-url", "origin"], target)
    unstaged = run(["git", "diff", "--stat"], target)
    staged = run(["git", "diff", "--cached", "--stat"], target)
    recent_commits = ""
    if log_count > 0:
        recent_commits = run([
            "git", "log", f"--max-count={log_count}", "--oneline", "--graph",
            "--pretty=format:%h %d %s (%an, %ar)",
        ], target)

    context = {
        "repo_name": repo_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "path": target,
        "git": {
            "branch": branch,
            "remote": sanitize_remote(remote),
            "working_tree": "dirty" if unstaged or staged else "clean",
            "unstaged_changes": unstaged,
            "staged_changes": staged,
        },
        "recent_commits": recent_commits.splitlines() if recent_commits else [],
        "branches": run(["git", "branch", "-a"], target).splitlines(),
        "project_structure": project_structure(target, target, ignored=DEFAULT_IGNORE, depth=depth),
        "project_tree": tree(target, ignored=DEFAULT_IGNORE, depth=depth),
    }

    if include_files:
        context["file_contents"] = collect_file_contents(target)
    return context


def render_markdown(context, depth):
    sections = []
    sections.append(f"# git-context: {context['repo_name']}")
    generated = datetime.fromisoformat(context["generated_at"]).strftime('%Y-%m-%d %H:%M:%S')
    sections.append(f"Generated: {generated}")
    sections.append(f"Path: {context['path']}")
    sections.append("")

    git = context["git"]
    sections.append(f"## Git Info\n- Branch: `{git['branch']}`")
    sections.append(f"- Remote: {git['remote']}")
    status = ""
    if git["unstaged_changes"]:
        status += f"\n- Unstaged changes: {git['unstaged_changes'].split(chr(10))[-1]}"
    if git["staged_changes"]:
        status += f"\n- Staged changes: {git['staged_changes'].split(chr(10))[-1]}"
    if git["working_tree"] == "clean":
        status += "\n- Working tree: clean"
    sections.append(status)

    if context["recent_commits"]:
        sections.append(f"\n## Recent Commits (last {len(context['recent_commits'])})")
        sections.append("```\n" + "\n".join(context["recent_commits"]) + "\n```")

    if context["branches"]:
        sections.append("\n## Branches")
        sections.append("```\n" + "\n".join(context["branches"]) + "\n```")

    sections.append(f"\n## Project Structure (depth={depth})")
    sections.append(f"```\n{context['project_tree']}\n```")

    if "file_contents" in context and context["file_contents"]["files"]:
        sections.append("\n## File Contents")
        for item in context["file_contents"]["files"]:
            sections.append(f"\n--- {item['path']} ---\n```{item['language']}\n{item['content']}\n```")
            if item["truncated"]:
                sections.append(f"\n... (truncated, more files in {item['path']})")

    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description='Generate AI-friendly context for a git repo')
    parser.add_argument('--depth', type=int, default=4, help='Directory tree depth (default: 4)')
    parser.add_argument('--files', action='store_true', help='Include source file contents')
    parser.add_argument('--log', type=int, default=20, help='Number of recent commits (default: 20, 0=skip)')
    parser.add_argument('--output', '-o', help='Write to file instead of stdout')
    parser.add_argument('--dir', default=os.getcwd(), help='Target directory (default: cwd)')
    parser.add_argument('--json', action='store_true', help='Output structured JSON instead of markdown')
    args = parser.parse_args()

    target = os.path.abspath(args.dir)
    if not os.path.isdir(os.path.join(target, '.git')):
        print(f"Not a git repo: {target}", file=sys.stderr)
        sys.exit(1)

    context = collect_context(target, depth=args.depth, log_count=args.log, include_files=args.files)
    output = json.dumps(context, indent=2) if args.json else render_markdown(context, args.depth)

    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Written to {args.output}")
    else:
        print(output)
