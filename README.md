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

## Install With uv

For normal use, install the CLI as a persistent uv tool:

```bash
uv tool install codex-tool-mocks
codex-tool-mocks --help
```

Then install the Codex plugin globally:

```bash
codex-tool-mocks install-global
```

This is the recommended uv workflow because Codex hooks will keep using the
Python environment created by `uv tool install`.

To install from a local checkout instead of a package index:

```bash
uv tool install .
codex-tool-mocks install-global
```

To try the CLI without installing it persistently:

```bash
uvx --from codex-tool-mocks codex-tool-mocks --help
```

If you use `uvx` to install the Codex plugin, make the hook re-run through `uvx`
so it does not depend on the temporary uvx environment:

```bash
uvx --from codex-tool-mocks codex-tool-mocks install-global --hook-runner uvx
```

For local development from this checkout:

```bash
uv sync
uv run codex-tool-mocks --help
uv run codex-tool-mocks install-global
```

## Install With pip

Install from a package index with pip:

```bash
pip install codex-tool-mocks
codex-tool-mocks --help
```

Initialize mock storage in the project you want to test:

```bash
codex-tool-mocks init
```

Then add fixtures:

```bash
codex-tool-mocks add-shell --id git-status --command "git status --short" --stdout "" --exit-code 0
```

To install the Codex plugin globally after a persistent `pip` or `uv tool`
install:

```bash
codex-tool-mocks install-global
```

The installer copies the plugin into `~/.codex/plugins/cache/debug/codex-tool-mocks/local`
and enables these entries in `~/.codex/config.toml`. The installed hook command
uses the Python environment that ran the installer, so the package must remain
installed there.

```toml
[features]
plugins = true
plugin_hooks = true

[plugins."codex-tool-mocks@debug"]
enabled = true
```

You can preview target paths without writing files:

```bash
codex-tool-mocks install-global --dry-run
```

More examples are in [docs/usage.md](docs/usage.md).
