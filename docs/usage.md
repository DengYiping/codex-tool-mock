# Using codex-tool-mock

`codex-tool-mock` lets you test Codex skills and agent workflows by replacing
shell-like tool calls with deterministic mocked responses. The MVP supports Codex
hook calls exposed as `toolName: "Bash"` with a `toolInput.command` string.

## Install With uv

For normal use, install the CLI as a persistent uv tool:

```bash
uv tool install codex-tool-mock
codex-tool-mock --help
```

Then install the Codex plugin globally:

```bash
codex-tool-mock install-global
```

The installed Codex hook will run the Python environment created by
`uv tool install`, so keep the uv tool installed while using the plugin.

To install from a local checkout instead of a package index:

```bash
uv tool install .
codex-tool-mock install-global
```

For one-off CLI usage without a persistent install:

```bash
uvx --from codex-tool-mock codex-tool-mock --help
```

If you use `uvx` to install the Codex plugin, make the installed hook re-run
through `uvx`:

```bash
uvx --from codex-tool-mock codex-tool-mock install-global --hook-runner uvx
```

From this repository during development:

```bash
uv sync
uv run codex-tool-mock --help
uv run codex-tool-mock install-global
```

## Install With pip

Install from a package index with pip:

```bash
pip install codex-tool-mock
codex-tool-mock --help
```

## Initialize A Project

Run this in the project where you want Codex to use mocks:

```bash
codex-tool-mock init
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

After installing the package persistently with `pip` or `uv tool`, install the
Codex plugin into the global Codex plugin cache:

```bash
codex-tool-mock install-global
```

From this repository during development, run the same installer through uv:

```bash
uv run codex-tool-mock install-global
```

The installer:

1. Copies the bundled plugin template to `~/.codex/plugins/cache/debug/codex-tool-mock/local`.
2. Rewrites the installed hook command so it runs the installed `codex_tool_mock` package.
3. Enables plugins and plugin hooks in `~/.codex/config.toml`.
4. Enables `[plugins."codex-tool-mock@debug"]`.

By default, the installed hook command uses the Python executable that ran
`codex-tool-mock install-global`:

```bash
<python> -m codex_tool_mock.hook
```

That works for `pip install`, `uv tool install`, and local `uv run` workflows as
long as the package remains installed in that environment.

For a one-shot `uvx` install, write a hook that re-runs through `uvx` whenever
Codex invokes the plugin:

```bash
uvx --from codex-tool-mock codex-tool-mock install-global --hook-runner uvx
```

If the package is not published under `codex-tool-mock`, pass any uv-supported
package spec:

```bash
uvx --from ./codex-tool-mock codex-tool-mock install-global \
  --hook-runner uvx \
  --package-spec ./codex-tool-mock
```

Use `CODEX_HOME` or `--codex-home` to target a different Codex home:

```bash
CODEX_HOME=/tmp/codex-home codex-tool-mock install-global
```

Preview without writing:

```bash
codex-tool-mock install-global --dry-run
```

Print the plugin path:

```bash
codex-tool-mock plugin-path
```

Use that path when inspecting the bundled plugin template. The global installer is
the supported way to enable it for Codex. The bundled plugin registers
`PreToolUse` and `PostToolUse` command hooks for `Bash` calls.

## Add Static Mocks

Exact command match:

```bash
codex-tool-mock add-shell \
  --id git-status-clean \
  --command "git status --short" \
  --stdout "" \
  --stderr "" \
  --exit-code 0
```

Regex command match:

```bash
codex-tool-mock add-shell-regex \
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
codex-tool-mock add-python \
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
codex-tool-mock calls list
```

Clear recorded calls before a test:

```bash
codex-tool-mock calls clear
```

## Verify Calls In Pytest

Use the helper API from tests:

```python
from codex_tool_mock.pytest import (
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

from codex_tool_mock.pytest import assert_shell_called


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

- `No codex-tool-mock fixture matched`: add a fixture for the exact command or use
  a regex fixture.
- `uv executable was not found`: install uv and make sure it is on `PATH` for the
  Codex hook process.
- `responder returned invalid JSON`: make sure the responder writes only the JSON
  response object to stdout; write debug logs to stderr.
- Calls are not recorded: confirm the local Codex plugin is enabled and that the
  tool call is exposed as `toolName: "Bash"`.
