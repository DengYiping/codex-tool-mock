from pathlib import Path

import pytest

from codex_tool_mocks.pytest import (
    assert_call_sequence,
    assert_shell_called,
    assert_shell_not_called,
)
from codex_tool_mocks.store import append_jsonl


def record_call(root: Path, command: str) -> None:
    append_jsonl(
        root / ".codex" / "tool-mocks" / "calls.jsonl",
        {
            "phase": "pre",
            "toolName": "Bash",
            "toolInput": {"command": command},
            "cwd": str(root),
        },
    )


def test_assert_shell_called_counts_calls(tmp_path: Path) -> None:
    record_call(tmp_path, "git status")
    record_call(tmp_path, "git status")

    assert_shell_called("git status", times=2, project_root=tmp_path)

    with pytest.raises(AssertionError, match="expected 1"):
        assert_shell_called("git status", times=1, project_root=tmp_path)


def test_assert_shell_not_called(tmp_path: Path) -> None:
    record_call(tmp_path, "git status")

    assert_shell_not_called("git diff", project_root=tmp_path)

    with pytest.raises(AssertionError, match="expected no calls"):
        assert_shell_not_called("git status", project_root=tmp_path)


def test_assert_call_sequence(tmp_path: Path) -> None:
    record_call(tmp_path, "git status")
    record_call(tmp_path, "git diff")

    assert_call_sequence(["git status", "git diff"], project_root=tmp_path)

    with pytest.raises(AssertionError, match="sequence mismatch"):
        assert_call_sequence(["git diff", "git status"], project_root=tmp_path)
