import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List


def run_git_command(args: List[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_repo_root() -> str:
    return run_git_command(["rev-parse", "--show-toplevel"])


def get_branch() -> str:
    branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    return branch or "HEAD"


def get_status() -> str:
    return run_git_command(["status", "--short"])


def get_untracked_files() -> List[str]:
    output = run_git_command(["ls-files", "--others", "--exclude-standard"])
    return [line for line in output.splitlines() if line.strip()] if output else []


def get_staged_diff() -> str:
    return run_git_command(["diff", "--cached"])


def get_unstaged_diff() -> str:
    return run_git_command(["diff"])


def get_recent_commits(limit: int) -> List[Dict[str, str]]:
    output = run_git_command([
        "log",
        f"--max-count={limit}",
        "--pretty=format:%H%x1f%an%x1f%ad%x1f%s",
        "--date=iso",
    ])
    commits: List[Dict[str, str]] = []
    if not output:
        return commits

    for line in output.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 4:
            continue
        commits.append(
            {
                "hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "subject": parts[3],
            }
        )
    return commits


def build_context(commit_limit: int) -> Dict[str, Any]:
    root = get_repo_root()
    repository = os.path.basename(root) if root else os.path.basename(os.getcwd())

    return {
        "repository": repository,
        "root": root,
        "branch": get_branch(),
        "status": get_status(),
        "untracked_files": get_untracked_files(),
        "staged_diff": get_staged_diff(),
        "unstaged_diff": get_unstaged_diff(),
        "recent_commits": get_recent_commits(commit_limit),
    }


def render_text_context(context: Dict[str, Any]) -> str:
    sections: List[str] = []

    sections.append(f"Repository: {context['repository']}")
    if context.get("root"):
        sections.append(f"Root: {context['root']}")
    sections.append(f"Branch: {context['branch']}")

    status = context.get("status") or "Clean working tree"
    sections.append("\n## Status\n" + status)

    untracked = context.get("untracked_files") or []
    if untracked:
        sections.append("\n## Untracked Files\n" + "\n".join(untracked))

    commits = context.get("recent_commits") or []
    if commits:
        commit_lines = [
            f"- {commit['hash'][:7]} {commit['subject']} ({commit['author']}, {commit['date']})"
            for commit in commits
        ]
        sections.append("\n## Recent Commits\n" + "\n".join(commit_lines))

    staged_diff = context.get("staged_diff")
    if staged_diff:
        sections.append("\n## Staged Diff\n```diff\n" + staged_diff + "\n```")

    unstaged_diff = context.get("unstaged_diff")
    if unstaged_diff:
        sections.append("\n## Unstaged Diff\n```diff\n" + unstaged_diff + "\n```")

    return "\n".join(sections).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Show current git context")
    parser.add_argument(
        "--commits",
        type=int,
        default=10,
        help="Number of recent commits to include (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output git context as JSON",
    )
    args = parser.parse_args()

    context = build_context(args.commits)

    if args.json:
        print(json.dumps(context, indent=2))
    else:
        print(render_text_context(context), end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
