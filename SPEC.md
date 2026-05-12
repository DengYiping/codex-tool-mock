# codex-tool-mock Spec

## Summary

`codex-tool-mock` is a Python/uv project that provides a Codex plugin plus helper CLI
for testing agent behavior with mocked shell-like tool calls.

The MVP uses Codex `PreToolUse` hooks to record incoming Bash-style commands and rewrite
matched commands into harmless commands that emit mocked results. Mocked results can come
from static fixture data or a user-provided Python responder script. `PostToolUse` hooks
record final observed responses.

The MVP includes exact and regex shell command matching, and supports uv inline script
dependencies for responder scripts and standalone pytest-style verification scripts.

## MVP Behavior

- Support shell-like tools exposed to hooks as `toolName: "Bash"` with
  `toolInput.command`.
- Store project-local fixtures and recordings under `.codex/tool-mocks/`.
- Match commands by either `match.type: "exact"` with `command`, or
  `match.type: "regex"` with `pattern`.
- Match fixtures in file order; the first enabled match wins.
- Fail closed when no fixture matches.
- For matched mocks, support static responses and Python responders.
- Convert the selected response into a safe rewritten shell command that reproduces
  stdout, stderr, and exit code without running the original command.
- Python responders run only after a fixture match. There is no global fallback resolver
  in the MVP.

## Interfaces

Static exact fixture:

```json
{
  "id": "git-status-clean",
  "toolName": "Bash",
  "match": {
    "type": "exact",
    "command": "git status --short"
  },
  "response": {
    "stdout": "",
    "stderr": "",
    "exitCode": 0
  }
}
```

Static regex fixture:

```json
{
  "id": "git-status-any",
  "toolName": "Bash",
  "match": {
    "type": "regex",
    "pattern": "^git status( --short)?$"
  },
  "response": {
    "stdout": "",
    "stderr": "",
    "exitCode": 0
  }
}
```

Python responder fixture:

```json
{
  "id": "dynamic-date",
  "toolName": "Bash",
  "match": {
    "type": "exact",
    "command": "date"
  },
  "responder": {
    "type": "python",
    "path": ".codex/tool-mocks/responders/date.py"
  }
}
```

Python responders are executed with:

```bash
uv run --script .codex/tool-mocks/responders/date.py
```

They may define inline dependencies:

```python
# /// script
# dependencies = ["python-dateutil"]
# ///
```

Responder stdin is a JSON object containing the original hook input and the matched
fixture:

```json
{
  "hookInput": { "hookEventName": "PreToolUse" },
  "fixture": { "id": "dynamic-date" }
}
```

Responder stdout must be one JSON object:

```json
{
  "stdout": "text",
  "stderr": "",
  "exitCode": 0
}
```

Standalone pytest-style verification scripts can also be run with `uv run --script`,
and may declare dependencies inline.

## CLI

- `codex-tool-mock init`
- `codex-tool-mock add-shell --id ID --command CMD --stdout TEXT --stderr TEXT --exit-code N`
- `codex-tool-mock add-shell-regex --id ID --pattern PATTERN --stdout TEXT --stderr TEXT --exit-code N`
- `codex-tool-mock add-python --id ID --command CMD --path SCRIPT`
- `codex-tool-mock add-python-regex --id ID --pattern PATTERN --path SCRIPT`
- `codex-tool-mock calls list`
- `codex-tool-mock calls clear`
- `codex-tool-mock plugin-path`

## Milestones

- MVP: shell-only mocking, exact/regex matching, static responses, Python responders
  with uv inline dependencies, and pytest-style assertions.
- Milestone 2: consume-once mocks, fixture sets, and record-to-fixture workflows.
- Milestone 3: MCP recording and limited MCP input rewrite support where Codex supports
  `updatedInput`.
- Milestone 4: evaluation harness for running prompts/skills against fake environments.
- Milestone 5: possible Codex upstream hook extension to return a complete mocked tool
  response and skip execution for all tools.

## Test Plan

- Parse `PreToolUse` and `PostToolUse` hook payloads.
- Match exact commands.
- Match regex commands in fixture order.
- Handle invalid regex patterns clearly.
- Render static responses as safe rewritten shell commands.
- Execute Python responders via `uv run --script`.
- Validate responder JSON and error handling.
- Append/read JSONL call records.
- Verify pytest helper assertions and failure messages.

## Assumptions

- PyPI distribution name: `codex-tool-mock`.
- Project storage: `.codex/tool-mocks/`.
- MVP matching: exact and regex command matching, first enabled fixture wins.
- MVP Python execution: `uv run --script` for responder and verification scripts.
- Plugin installation is documented as local plugin usage, not marketplace publishing.
