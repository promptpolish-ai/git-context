import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent


def run_git_context(*args):
    return subprocess.run(
        [sys.executable, str(REPO / "git-context"), "--dir", str(REPO), *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )


def test_json_output_is_valid_and_structured():
    result = run_git_context("--json", "--log", "1")
    payload = json.loads(result.stdout)

    assert payload["repository"] == "git-context"
    assert payload["path"] == str(REPO)
    assert payload["git"]["branch"]
    assert "working_tree_clean" in payload["git"]
    assert isinstance(payload["commits"], list)
    assert len(payload["commits"]) <= 1
    assert isinstance(payload["branches"], list)
    assert isinstance(payload["tree"], list)
    assert "files" not in payload


def test_json_output_includes_files_when_requested():
    result = run_git_context("--json", "--files", "--log", "0")
    payload = json.loads(result.stdout)

    assert payload["commits"] == []
    assert payload["files"]
    assert all({"path", "language", "size", "content", "truncated"} <= set(item) for item in payload["files"])
    assert any(item["path"] == "README.md" for item in payload["files"])


def test_markdown_output_still_works():
    result = run_git_context("--log", "0")
    assert result.stdout.startswith("# git-context: git-context")
    assert "## Project Structure" in result.stdout
