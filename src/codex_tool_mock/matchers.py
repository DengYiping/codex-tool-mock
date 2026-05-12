"""Fixture matching for Codex tool mocks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class FixtureMatchError(ValueError):
    """Raised when a fixture cannot be evaluated."""


@dataclass(frozen=True)
class MatchResult:
    """Matched fixture metadata.

    Args:
        fixture: Fixture object.
        index: Fixture order index.
    """

    fixture: dict[str, Any]
    index: int


def find_matching_fixture(
    tool_name: str,
    command: str,
    fixtures: list[dict[str, Any]],
) -> MatchResult | None:
    """Find the first enabled fixture matching a tool command.

    Args:
        tool_name: Codex hook tool name.
        command: Shell command from hook input.
        fixtures: Fixture objects in storage order.

    Returns:
        Match result, or None when no fixture matches.
    """
    for index, fixture in enumerate(fixtures):
        if fixture.get("enabled", True) is False:
            continue
        if fixture.get("toolName", "Bash") != tool_name:
            continue
        if _matches_command(fixture, command):
            return MatchResult(fixture=fixture, index=index)
    return None


def _matches_command(fixture: dict[str, Any], command: str) -> bool:
    """Evaluate one fixture against a command.

    Args:
        fixture: Fixture object.
        command: Shell command.

    Returns:
        True when the fixture matches.
    """
    match = fixture.get("match")
    if match is None and "command" in fixture:
        match = {"type": "exact", "command": fixture["command"]}
    if not isinstance(match, dict):
        raise FixtureMatchError(f"fixture {fixture.get('id', '<unknown>')} has invalid match")
    match_type = match.get("type")
    if match_type == "exact":
        expected = match.get("command")
        if not isinstance(expected, str):
            raise FixtureMatchError(f"fixture {fixture.get('id', '<unknown>')} missing command")
        return command == expected
    if match_type == "regex":
        pattern = match.get("pattern")
        if not isinstance(pattern, str):
            raise FixtureMatchError(f"fixture {fixture.get('id', '<unknown>')} missing pattern")
        try:
            return re.search(pattern, command) is not None
        except re.error as error:
            raise FixtureMatchError(
                f"fixture {fixture.get('id', '<unknown>')} has invalid regex: {error}"
            ) from error
    raise FixtureMatchError(
        f"fixture {fixture.get('id', '<unknown>')} has unsupported match type {match_type!r}"
    )
