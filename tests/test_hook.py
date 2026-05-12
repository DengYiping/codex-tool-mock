import json
import os
import subprocess
import sys
from pathlib import Path

from codex_tool_mock.hook import handle_hook_payload, render_shell_response_command
from codex_tool_mock.store import append_jsonl, load_jsonl


def pre_tool_payload(command: str) -> dict:
    return {
        "sessionId": "session-1",
        "turnId": "turn-1",
        "transcriptPath": None,
        "cwd": "/tmp/project",
        "hookEventName": "PreToolUse",
        "model": "gpt-test",
        "permissionMode": "default",
        "toolName": "Bash",
        "toolInput": {"command": command},
        "toolUseId": "call-1",
    }


def post_tool_payload(command: str) -> dict:
    payload = pre_tool_payload(command)
    payload["hookEventName"] = "PostToolUse"
    payload["toolResponse"] = {"output": "done", "metadata": {"exit_code": 0}}
    return payload


def write_fixture(root: Path, fixture: dict) -> None:
    append_jsonl(root / ".codex" / "tool-mocks" / "mocks.jsonl", fixture)


def test_render_shell_response_command_replays_streams_and_exit_code() -> None:
    command = render_shell_response_command({"stdout": "out\n", "stderr": "err\n", "exitCode": 7})

    completed = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.stdout == "out\n"
    assert completed.stderr == "err\n"
    assert completed.returncode == 7


def test_pre_tool_use_static_mock_records_and_rewrites(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        {
            "id": "status",
            "toolName": "Bash",
            "match": {"type": "exact", "command": "git status --short"},
            "response": {"stdout": "", "stderr": "", "exitCode": 0},
        },
    )

    output = handle_hook_payload(pre_tool_payload("git status --short"), project_root=tmp_path)

    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert output["hookSpecificOutput"]["updatedInput"]["command"]
    calls = load_jsonl(tmp_path / ".codex" / "tool-mocks" / "calls.jsonl")
    assert calls[0]["matchedMockId"] == "status"
    assert calls[0]["phase"] == "pre"


def test_pre_tool_use_regex_static_mock(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        {
            "id": "status-regex",
            "toolName": "Bash",
            "match": {"type": "regex", "pattern": r"^git status( --short)?$"},
            "response": {"stdout": "clean\n", "stderr": "", "exitCode": 0},
        },
    )

    output = handle_hook_payload(pre_tool_payload("git status"), project_root=tmp_path)

    rewritten = output["hookSpecificOutput"]["updatedInput"]["command"]
    completed = subprocess.run(rewritten, shell=True, text=True, capture_output=True, check=False)
    assert completed.stdout == "clean\n"


def test_pre_tool_use_missing_mock_blocks_in_strict_mode(tmp_path: Path) -> None:
    output = handle_hook_payload(pre_tool_payload("rm -rf /tmp/nope"), project_root=tmp_path)

    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        "No codex-tool-mock fixture matched"
        in output["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_pre_tool_use_python_responder_with_uv_inline_dependencies(tmp_path: Path) -> None:
    responder = tmp_path / ".codex" / "tool-mocks" / "responders" / "date.py"
    responder.parent.mkdir(parents=True)
    responder.write_text(
        "\n".join(
            [
                "# /// script",
                "# dependencies = []",
                "# ///",
                "import json",
                "import sys",
                "payload = json.load(sys.stdin)",
                "command = payload['hookInput']['toolInput']['command']",
                "response = {'stdout': f'mocked {command}\\n', 'stderr': '', 'exitCode': 0}",
                "json.dump(response, sys.stdout)",
            ]
        ),
        encoding="utf-8",
    )
    write_fixture(
        tmp_path,
        {
            "id": "dynamic-date",
            "toolName": "Bash",
            "match": {"type": "exact", "command": "date"},
            "responder": {"type": "python", "path": ".codex/tool-mocks/responders/date.py"},
        },
    )

    output = handle_hook_payload(pre_tool_payload("date"), project_root=tmp_path)

    rewritten = output["hookSpecificOutput"]["updatedInput"]["command"]
    completed = subprocess.run(rewritten, shell=True, text=True, capture_output=True, check=False)
    assert completed.stdout == "mocked date\n"


def test_post_tool_use_records_response_summary(tmp_path: Path) -> None:
    output = handle_hook_payload(post_tool_payload("git status"), project_root=tmp_path)

    assert output == {"continue": True}
    calls = load_jsonl(tmp_path / ".codex" / "tool-mocks" / "calls.jsonl")
    assert calls[0]["phase"] == "post"
    assert calls[0]["toolResponse"] == {"output": "done", "metadata": {"exit_code": 0}}


def test_module_entrypoint_reads_stdin_and_writes_json(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        {
            "id": "echo",
            "toolName": "Bash",
            "match": {"type": "exact", "command": "echo hi"},
            "response": {"stdout": "hi\n", "stderr": "", "exitCode": 0},
        },
    )
    env = os.environ.copy()
    env["CODEX_TOOL_MOCKS_ROOT"] = str(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-m", "codex_tool_mock.hook"],
        input=json.dumps(pre_tool_payload("echo hi")),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
