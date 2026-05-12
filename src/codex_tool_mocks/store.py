"""Project-local fixture and call recording storage."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

TOOL_MOCKS_DIR = Path(".codex") / "tool-mocks"
MOCKS_FILE = TOOL_MOCKS_DIR / "mocks.jsonl"
CALLS_FILE = TOOL_MOCKS_DIR / "calls.jsonl"


def resolve_project_root(project_root: Path | str | None = None) -> Path:
    """Resolve the project root for fixture and call storage.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Absolute project root path.
    """
    if project_root is not None:
        return Path(project_root).expanduser().resolve()
    env_root = os.environ.get("CODEX_TOOL_MOCKS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path.cwd().resolve()


def tool_mocks_dir(project_root: Path | str | None = None) -> Path:
    """Return the project-local tool mocks directory.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Absolute `.codex/tool-mocks` path.
    """
    return resolve_project_root(project_root) / TOOL_MOCKS_DIR


def mocks_file(project_root: Path | str | None = None) -> Path:
    """Return the fixture JSONL path.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Absolute fixture path.
    """
    return resolve_project_root(project_root) / MOCKS_FILE


def calls_file(project_root: Path | str | None = None) -> Path:
    """Return the call recording JSONL path.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Absolute call log path.
    """
    return resolve_project_root(project_root) / CALLS_FILE


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    """Append one JSON object to a JSONL file.

    Args:
        path: JSONL file path.
        value: Object to append.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.write("\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSON objects from a JSONL file.

    Args:
        path: JSONL file path.

    Returns:
        Parsed JSON objects. Missing files return an empty list.
    """
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(value)
    return records


def load_fixtures(project_root: Path | str | None = None) -> list[dict[str, Any]]:
    """Load mock fixtures.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Fixture records.
    """
    return load_jsonl(mocks_file(project_root))


def append_fixture(fixture: dict[str, Any], project_root: Path | str | None = None) -> None:
    """Append a mock fixture.

    Args:
        fixture: Fixture object.
        project_root: Optional explicit project root.

    Returns:
        None.
    """
    append_jsonl(mocks_file(project_root), fixture)


def record_call(record: dict[str, Any], project_root: Path | str | None = None) -> None:
    """Append a tool call record.

    Args:
        record: Call record object.
        project_root: Optional explicit project root.

    Returns:
        None.
    """
    append_jsonl(calls_file(project_root), record)


def load_calls(project_root: Path | str | None = None) -> list[dict[str, Any]]:
    """Load recorded tool calls.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Recorded call objects.
    """
    return load_jsonl(calls_file(project_root))


def clear_calls(project_root: Path | str | None = None) -> None:
    """Clear recorded tool calls.

    Args:
        project_root: Optional explicit project root.

    Returns:
        None.
    """
    path = calls_file(project_root)
    if path.exists():
        path.unlink()


def init_storage(project_root: Path | str | None = None) -> Path:
    """Create project-local storage directories.

    Args:
        project_root: Optional explicit project root.

    Returns:
        Created `.codex/tool-mocks` path.
    """
    root = tool_mocks_dir(project_root)
    (root / "responders").mkdir(parents=True, exist_ok=True)
    mocks = mocks_file(project_root)
    if not mocks.exists():
        mocks.parent.mkdir(parents=True, exist_ok=True)
        mocks.write_text("", encoding="utf-8")
    return root
