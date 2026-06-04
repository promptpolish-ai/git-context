#!/usr/bin/env python3
"""Main entry point for git-context."""

import argparse
import json
import os
import subprocess
import sys


def get_git_context() -> dict:
    """Collect git context information."""
    context = {}
    
    # Get current branch
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        context["branch"] = branch
    except subprocess.CalledProcessError:
        context["branch"] = None
    
    # Get latest commit hash
    try:
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        context["commit_hash"] = commit_hash
    except subprocess.CalledProcessError:
        context["commit_hash"] = None
    
    # Get latest commit message
    try:
        commit_msg = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        context["commit_message"] = commit_msg
    except subprocess.CalledProcessError:
        context["commit_message"] = None
    
    # Get diff (staged + unstaged)
    try:
        diff = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout
        context["diff"] = diff
    except subprocess.CalledProcessError:
        context["diff"] = None
    
    # Get list of changed files
    try:
        changed_files = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip().split("\n")
        context["changed_files"] = [f for f in changed_files if f]
    except subprocess.CalledProcessError:
        context["changed_files"] = []
    
    # Get remote URL
    try:
        remote_url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        context["remote_url"] = remote_url
    except subprocess.CalledProcessError:
        context["remote_url"] = None
    
    return context


def format_text(context: dict) -> str:
    """Format context as human-readable text."""
    lines = []
    lines.append("=== Git Context ===")
    lines.append(f"Branch: {context.get('branch', 'N/A')}")
    lines.append(f"Commit: {context.get('commit_hash', 'N/A')}")
    lines.append(f"Message: {context.get('commit_message', 'N/A')}")
    lines.append(f"Remote: {context.get('remote_url', 'N/A')}")
    lines.append(f"Changed files: {', '.join(context.get('changed_files', [])) or 'None'}")
    lines.append("")
    lines.append("--- Diff ---")
    lines.append(context.get('diff', 'No diff available.'))
    return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Collect git context for AI prompts."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output context in JSON format instead of plain text."
    )
    args = parser.parse_args()
    
    context = get_git_context()
    
    if args.json:
        print(json.dumps(context, indent=2))
    else:
        print(format_text(context))


if __name__ == "__main__":
    main()
