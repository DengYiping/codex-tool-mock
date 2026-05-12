# codex-tool-mocks

Codex tool mocking plugin and CLI. Useful for testing and evaluating skills on
Codex by mocking shell-like tool calls and asserting that expected commands were
used.

See [docs/usage.md](docs/usage.md) for setup and usage. See [SPEC.md](SPEC.md)
for the MVP behavior and milestone plan.

## MVP

- Shell-like `Bash` hook support.
- Exact and regex command matching.
- Static mocked stdout/stderr/exit code responses.
- Python responder scripts executed through `uv run --script`, including uv inline
  dependency metadata.
- Project-local fixtures and recordings under `.codex/tool-mocks/`.
- Pytest-style verification helpers.

## Quick Start

```bash
uv sync
uv run codex-tool-mocks init
uv run codex-tool-mocks add-shell --id git-status --command "git status --short" --stdout "" --exit-code 0
uv run codex-tool-mocks plugin-path
```
