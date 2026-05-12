"""Pytest-style verification helpers for recorded Codex tool calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codex_tool_mock.store import load_calls as _load_calls


def load_calls(project_root: Path | str | None = None) -> list[dict[str, Any]]:
    """Load recorded calls.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Recorded call objects.
    """
    return _load_calls(project_root)


def assert_shell_called(
    command: str,
    *,
    times: int | None = None,
    cwd: str | None = None,
    project_root: Path | str | None = None,
) -> None:
    """Assert that a shell command was recorded.

    Args:
        command: Expected command.
        times: Optional exact call count.
        cwd: Optional expected working directory.
        project_root: Optional explicit project root.

    Returns:
        None.
    """
    matches = _matching_pre_calls(command, cwd=cwd, project_root=project_root)
    if times is None:
        if not matches:
            raise AssertionError(f"expected shell command {command!r} to be called")
        return
    if len(matches) != times:
        raise AssertionError(
            f"expected {times} calls to shell command {command!r}, found {len(matches)}"
        )


def assert_shell_not_called(
    command: str,
    *,
    cwd: str | None = None,
    project_root: Path | str | None = None,
) -> None:
    """Assert that a shell command was not recorded.

    Args:
        command: Unexpected command.
        cwd: Optional working directory filter.
        project_root: Optional explicit project root.

    Returns:
        None.
    """
    matches = _matching_pre_calls(command, cwd=cwd, project_root=project_root)
    if matches:
        raise AssertionError(
            f"expected no calls to shell command {command!r}, found {len(matches)}"
        )


def assert_call_sequence(
    commands: list[str],
    *,
    project_root: Path | str | None = None,
) -> None:
    """Assert the recorded shell pre-call command sequence.

    Args:
        commands: Expected ordered commands.
        project_root: Optional explicit project root.

    Returns:
        None.
    """
    actual = [
        call.get("toolInput", {}).get("command")
        for call in load_calls(project_root)
        if call.get("phase") == "pre" and call.get("toolName") == "Bash"
    ]
    if actual != commands:
        raise AssertionError(f"sequence mismatch: expected {commands!r}, found {actual!r}")


def _matching_pre_calls(
    command: str,
    *,
    cwd: str | None,
    project_root: Path | str | None,
) -> list[dict[str, Any]]:
    """Return recorded pre-calls matching a command.

    Args:
        command: Expected command.
        cwd: Optional working directory.
        project_root: Optional explicit project root.

    Returns:
        Matching call records.
    """
    calls = []
    for call in load_calls(project_root):
        if call.get("phase") != "pre" or call.get("toolName") != "Bash":
            continue
        tool_input = call.get("toolInput", {})
        if not isinstance(tool_input, dict) or tool_input.get("command") != command:
            continue
        if cwd is not None and call.get("cwd") != cwd:
            continue
        calls.append(call)
    return calls
