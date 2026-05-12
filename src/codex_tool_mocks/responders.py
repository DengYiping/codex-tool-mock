"""Static and Python-script mock responders."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class ResponderError(RuntimeError):
    """Raised when a mock responder cannot produce a valid response."""


def response_from_fixture(
    fixture: dict[str, Any],
    hook_input: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Resolve a fixture into a shell response object.

    Args:
        fixture: Matched fixture object.
        hook_input: Codex hook input.
        project_root: Project root.

    Returns:
        Response object with stdout, stderr, and exitCode.
    """
    if "response" in fixture:
        response = fixture["response"]
    elif "responder" in fixture:
        response = run_python_responder(fixture, hook_input, project_root)
    else:
        raise ResponderError(f"fixture {fixture.get('id', '<unknown>')} has no response")
    return validate_response(response, fixture_id=str(fixture.get("id", "<unknown>")))


def run_python_responder(
    fixture: dict[str, Any],
    hook_input: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Run a Python responder script through uv.

    Args:
        fixture: Matched fixture object.
        hook_input: Codex hook input.
        project_root: Project root.

    Returns:
        Parsed responder response.
    """
    responder = fixture.get("responder")
    if not isinstance(responder, dict) or responder.get("type") != "python":
        raise ResponderError(f"fixture {fixture.get('id', '<unknown>')} has invalid responder")
    path_value = responder.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ResponderError(f"fixture {fixture.get('id', '<unknown>')} responder missing path")
    script_path = (project_root / path_value).resolve()
    if not script_path.exists():
        raise ResponderError(f"responder script does not exist: {script_path}")
    uv = shutil.which("uv")
    if uv is None:
        raise ResponderError("uv executable was not found for Python responder")
    payload = {"hookInput": hook_input, "fixture": fixture}
    completed = subprocess.run(
        [uv, "run", "--script", str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=project_root,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        detail = f": {stderr}" if stderr else ""
        raise ResponderError(
            f"responder {script_path} exited with code {completed.returncode}{detail}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ResponderError(f"responder {script_path} returned invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ResponderError(f"responder {script_path} returned non-object JSON")
    return value


def validate_response(response: Any, *, fixture_id: str) -> dict[str, Any]:
    """Validate and normalize a mock response.

    Args:
        response: Candidate response object.
        fixture_id: Fixture identifier for diagnostics.

    Returns:
        Normalized response object.
    """
    if not isinstance(response, dict):
        raise ResponderError(f"fixture {fixture_id} response must be an object")
    stdout = response.get("stdout", "")
    stderr = response.get("stderr", "")
    exit_code = response.get("exitCode", 0)
    if not isinstance(stdout, str):
        raise ResponderError(f"fixture {fixture_id} response stdout must be a string")
    if not isinstance(stderr, str):
        raise ResponderError(f"fixture {fixture_id} response stderr must be a string")
    if not isinstance(exit_code, int):
        raise ResponderError(f"fixture {fixture_id} response exitCode must be an integer")
    if exit_code < 0 or exit_code > 255:
        raise ResponderError(f"fixture {fixture_id} response exitCode must be between 0 and 255")
    return {"stdout": stdout, "stderr": stderr, "exitCode": exit_code}
