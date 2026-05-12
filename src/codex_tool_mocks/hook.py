"""Codex hook entrypoint for shell-like tool mocks."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any

from codex_tool_mocks.matchers import FixtureMatchError, find_matching_fixture
from codex_tool_mocks.responders import ResponderError, response_from_fixture
from codex_tool_mocks.store import load_fixtures, record_call, resolve_project_root


def handle_hook_payload(
    payload: dict[str, Any],
    *,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    """Handle one Codex hook payload.

    Args:
        payload: Hook input from Codex.
        project_root: Optional explicit project root.

    Returns:
        Hook output JSON object.
    """
    root = resolve_project_root(project_root)
    event_name = payload.get("hookEventName")
    if event_name == "PreToolUse":
        return _handle_pre_tool_use(payload, root)
    if event_name == "PostToolUse":
        return _handle_post_tool_use(payload, root)
    return {"continue": True}


def render_shell_response_command(response: dict[str, Any]) -> str:
    """Render a safe shell command that replays a mock response.

    Args:
        response: Valid response object.

    Returns:
        Shell command string.
    """
    script = (
        "import base64, sys; "
        f"sys.stdout.buffer.write(base64.b64decode({_python_string(_b64(response['stdout']))})); "
        f"sys.stderr.buffer.write(base64.b64decode({_python_string(_b64(response['stderr']))})); "
        f"raise SystemExit({int(response['exitCode'])})"
    )
    return f"python3 -c {_shell_single_quote(script)}"


def main() -> None:
    """Run the hook CLI.

    Args:
        None.

    Returns:
        None.
    """
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        output = handle_hook_payload(payload)
        json.dump(output, sys.stdout)
        sys.stdout.write("\n")
    except (FixtureMatchError, ResponderError, ValueError, json.JSONDecodeError) as error:
        output = _deny_pre_tool_use(f"codex-tool-mocks hook failed: {error}")
        json.dump(output, sys.stdout)
        sys.stdout.write("\n")


def _handle_pre_tool_use(payload: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Handle a PreToolUse payload.

    Args:
        payload: Hook input.
        project_root: Project root.

    Returns:
        Hook output.
    """
    tool_name = str(payload.get("toolName", ""))
    tool_input = payload.get("toolInput", {})
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return {"continue": True}
    fixtures = load_fixtures(project_root)
    match = find_matching_fixture(tool_name, command, fixtures)
    if match is None:
        _record(
            payload,
            project_root,
            {
                "phase": "pre",
                "command": command,
                "matchedMockId": None,
            },
        )
        return _deny_pre_tool_use(f"No codex-tool-mocks fixture matched command: {command}")
    fixture = match.fixture
    response = response_from_fixture(fixture, payload, project_root)
    rewritten_command = render_shell_response_command(response)
    _record(
        payload,
        project_root,
        {
            "phase": "pre",
            "command": command,
            "matchedMockId": str(fixture.get("id", "")),
            "fixtureIndex": match.index,
            "mockResponse": response,
        },
    )
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"command": rewritten_command},
        },
    }


def _handle_post_tool_use(payload: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Handle a PostToolUse payload.

    Args:
        payload: Hook input.
        project_root: Project root.

    Returns:
        Hook output.
    """
    tool_input = payload.get("toolInput", {})
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    _record(
        payload,
        project_root,
        {
            "phase": "post",
            "command": command if isinstance(command, str) else None,
            "matchedMockId": None,
            "toolResponse": payload.get("toolResponse"),
        },
    )
    return {"continue": True}


def _record(
    payload: dict[str, Any],
    project_root: Path,
    details: dict[str, Any],
) -> None:
    """Record a hook-observed tool call.

    Args:
        payload: Hook input.
        project_root: Project root.
        details: Phase-specific record fields.

    Returns:
        None.
    """
    record: dict[str, Any] = {
        "sessionId": payload.get("sessionId"),
        "turnId": payload.get("turnId"),
        "toolUseId": payload.get("toolUseId"),
        "cwd": payload.get("cwd"),
        "toolName": payload.get("toolName"),
        "toolInput": payload.get("toolInput"),
    }
    record.update({key: value for key, value in details.items() if value is not None})
    record_call(record, project_root)


def _deny_pre_tool_use(reason: str) -> dict[str, Any]:
    """Build a PreToolUse denial output.

    Args:
        reason: Denial reason.

    Returns:
        Hook output object.
    """
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def _b64(text: str) -> str:
    """Base64 encode text.

    Args:
        text: Text to encode.

    Returns:
        Base64 encoded text.
    """
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _python_string(value: str) -> str:
    """Render a Python string literal.

    Args:
        value: String value.

    Returns:
        JSON-backed Python string literal.
    """
    return json.dumps(value)


def _shell_single_quote(value: str) -> str:
    """Render a single-quoted shell token.

    Args:
        value: Shell token value.

    Returns:
        Safely quoted token.
    """
    return "'" + value.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    main()
