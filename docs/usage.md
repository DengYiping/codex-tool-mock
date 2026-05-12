# Using codex-tool-mocks

`codex-tool-mocks` lets you test Codex skills and agent workflows by replacing
shell-like tool calls with deterministic mocked responses. The MVP supports Codex
hook calls exposed as `toolName: "Bash"` with a `toolInput.command` string.

## Install For Development

From this repository:

```bash
uv sync
```

Check that the CLI is available:

```bash
uv run codex-tool-mocks --help
```

## Initialize A Project

Run this in the project where you want Codex to use mocks:

```bash
uv run codex-tool-mocks init
```

This creates:

```text
.codex/tool-mocks/
  mocks.jsonl
  responders/
```

Call recordings are written to:

```text
.codex/tool-mocks/calls.jsonl
```

## Enable The Codex Plugin

Print the plugin path:

```bash
uv run codex-tool-mocks plugin-path
```

Use that path when installing or enabling this as a local Codex plugin. The bundled
plugin registers `PreToolUse` and `PostToolUse` command hooks for `Bash` calls.

The hook command runs:

```bash
uv run --project "<repo-root>" python -m codex_tool_mocks.hook
```

## Add Static Mocks

Exact command match:

```bash
uv run codex-tool-mocks add-shell \
  --id git-status-clean \
  --command "git status --short" \
  --stdout "" \
  --stderr "" \
  --exit-code 0
```

Regex command match:

```bash
uv run codex-tool-mocks add-shell-regex \
  --id git-status-any \
  --pattern "^git status( --short)?$" \
  --stdout "" \
  --stderr "" \
  --exit-code 0
```

Fixtures are stored as JSONL in file order. The first enabled fixture that matches
the command wins.

## Add A Python Responder

Use a Python responder when the mocked output should be computed dynamically.

Create `.codex/tool-mocks/responders/date.py`:

```python
# /// script
# dependencies = []
# ///

import json
import sys

payload = json.load(sys.stdin)
command = payload["hookInput"]["toolInput"]["command"]

json.dump(
    {
        "stdout": f"mocked response for {command}\n",
        "stderr": "",
        "exitCode": 0,
    },
    sys.stdout,
)
```

Register it:

```bash
uv run codex-tool-mocks add-python \
  --id dynamic-date \
  --command "date" \
  --path ".codex/tool-mocks/responders/date.py"
```

Python responders are run with:

```bash
uv run --script <responder-path>
```

That means responders can declare inline uv dependencies:

```python
# /// script
# dependencies = ["python-dateutil"]
# ///
```

Responder stdin contains:

```json
{
  "hookInput": {
    "hookEventName": "PreToolUse",
    "toolName": "Bash",
    "toolInput": {
      "command": "date"
    }
  },
  "fixture": {
    "id": "dynamic-date"
  }
}
```

Responder stdout must be a JSON object with:

```json
{
  "stdout": "text to write to stdout",
  "stderr": "text to write to stderr",
  "exitCode": 0
}
```

If a responder exits nonzero, emits invalid JSON, or returns invalid fields, the
hook blocks the tool call with a clear error.

## What Happens At Runtime

When Codex calls a matching shell-like tool:

1. The `PreToolUse` hook records the attempted command.
2. The hook finds the first matching fixture.
3. The hook rewrites the command into a safe `python3 -c ...` command.
4. Codex runs the rewritten command instead of the original command.
5. The `PostToolUse` hook records the final tool response summary.

When no fixture matches, the hook fails closed and denies the command.

## Inspect Calls

List recorded calls:

```bash
uv run codex-tool-mocks calls list
```

Clear recorded calls before a test:

```bash
uv run codex-tool-mocks calls clear
```

## Verify Calls In Pytest

Use the helper API from tests:

```python
from codex_tool_mocks.pytest import (
    assert_call_sequence,
    assert_shell_called,
    assert_shell_not_called,
)


def test_skill_used_expected_commands():
    assert_shell_called("git status --short", times=1)
    assert_shell_not_called("rm -rf /tmp/example")
    assert_call_sequence(["git status --short"])
```

You can also write a standalone verification script and run it with uv inline
dependencies:

```python
# /// script
# dependencies = ["pytest"]
# ///

from codex_tool_mocks.pytest import assert_shell_called


def test_git_status_was_called():
    assert_shell_called("git status --short", times=1)
```

Run it:

```bash
uv run --script verify_skill.py
```

## Fixture File Format

Static exact fixture:

```json
{"id":"git-status-clean","toolName":"Bash","match":{"type":"exact","command":"git status --short"},"response":{"stdout":"","stderr":"","exitCode":0}}
```

Static regex fixture:

```json
{"id":"git-status-any","toolName":"Bash","match":{"type":"regex","pattern":"^git status( --short)?$"},"response":{"stdout":"","stderr":"","exitCode":0}}
```

Python responder fixture:

```json
{"id":"dynamic-date","toolName":"Bash","match":{"type":"exact","command":"date"},"responder":{"type":"python","path":".codex/tool-mocks/responders/date.py"}}
```

## Troubleshooting

- `No codex-tool-mocks fixture matched`: add a fixture for the exact command or use
  a regex fixture.
- `uv executable was not found`: install uv and make sure it is on `PATH` for the
  Codex hook process.
- `responder returned invalid JSON`: make sure the responder writes only the JSON
  response object to stdout; write debug logs to stderr.
- Calls are not recorded: confirm the local Codex plugin is enabled and that the
  tool call is exposed as `toolName: "Bash"`.
