# codex-tool-mock

[![PyPI](https://img.shields.io/pypi/v/codex-tool-mock.svg)](https://pypi.org/project/codex-tool-mock/)

Codex tool mocking plugin and CLI. Useful for testing and evaluating skills on
Codex by mocking shell-like tool calls and asserting that expected commands were
used.

See [docs/usage.md](docs/usage.md) for setup and usage, [docs/publishing.md](docs/publishing.md)
for PyPI publishing, and [SPEC.md](SPEC.md) for the MVP behavior and milestone plan.

## MVP

- Shell-like `Bash` hook support.
- Exact and regex command matching.
- Static mocked stdout/stderr/exit code responses.
- Python responder scripts executed through `uv run --script`, including uv inline
  dependency metadata.
- Project-local fixtures and recordings under `.codex/tool-mocks/`.
- Pytest-style verification helpers.

## Install With uv

```bash
uv tool install codex-tool-mock
codex-tool-mock --help
```

Then install the Codex plugin globally:

```bash
codex-tool-mock install-global
```

This is the recommended uv workflow because Codex hooks will keep using the
Python environment created by `uv tool install`.

To install from a local checkout instead of a package index:

```bash
uv tool install .
codex-tool-mock install-global
```

To try the CLI without installing it persistently:

```bash
uvx --from codex-tool-mock codex-tool-mock --help
```

If you use `uvx` to install the Codex plugin, make the hook re-run through `uvx`
so it does not depend on the temporary uvx environment:

```bash
uvx --from codex-tool-mock codex-tool-mock install-global --hook-runner uvx
```

For local development from this checkout:

```bash
uv sync
uv run codex-tool-mock --help
uv run codex-tool-mock install-global
```

## Install With pip

You can also install directly from PyPI with pip, without cloning this
repository:

```bash
pip install codex-tool-mock
codex-tool-mock --help
```

Initialize mock storage in the project you want to test:

```bash
codex-tool-mock init
```

Then add fixtures:

```bash
codex-tool-mock add-shell --id git-status --command "git status --short" --stdout "" --exit-code 0
```

To install the Codex plugin globally after a persistent `pip` or `uv tool`
install:

```bash
codex-tool-mock install-global
```

The installer copies the plugin into `~/.codex/plugins/cache/debug/codex-tool-mock/local`
and enables these entries in `~/.codex/config.toml`. The installed hook command
uses the Python environment that ran the installer, so the package must remain
installed there.

```toml
[features]
plugins = true
plugin_hooks = true

[plugins."codex-tool-mock@debug"]
enabled = true
```

You can preview target paths without writing files:

```bash
codex-tool-mock install-global --dry-run
```

More examples are in [docs/usage.md](docs/usage.md).
