"""Command-line interface for codex-tool-mocks."""

from __future__ import annotations

import argparse
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from codex_tool_mocks.install import PLUGIN_KEY, install_global_plugin
from codex_tool_mocks.store import (
    append_fixture,
    clear_calls,
    init_storage,
    load_calls,
)


def main(argv: list[str] | None = None) -> None:
    """Run the codex-tool-mocks CLI.

    Args:
        argv: Optional argument vector.

    Returns:
        None.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser.

    Args:
        None.

    Returns:
        Configured parser.
    """
    parser = argparse.ArgumentParser(prog="codex-tool-mocks")
    parser.add_argument("--root", type=Path, default=None, help="Project root.")
    subcommands = parser.add_subparsers(required=True)

    init_parser = subcommands.add_parser("init", help="Create project-local mock storage.")
    init_parser.set_defaults(func=_cmd_init)

    add_shell = subcommands.add_parser("add-shell", help="Add an exact shell static mock.")
    _add_response_args(add_shell)
    add_shell.add_argument("--command", required=True)
    add_shell.set_defaults(func=_cmd_add_shell)

    add_shell_regex = subcommands.add_parser(
        "add-shell-regex", help="Add a regex shell static mock."
    )
    _add_response_args(add_shell_regex)
    add_shell_regex.add_argument("--pattern", required=True)
    add_shell_regex.set_defaults(func=_cmd_add_shell_regex)

    add_python = subcommands.add_parser("add-python", help="Add an exact shell Python responder.")
    add_python.add_argument("--id", required=True)
    add_python.add_argument("--command", required=True)
    add_python.add_argument("--path", required=True)
    add_python.set_defaults(func=_cmd_add_python)

    add_python_regex = subcommands.add_parser(
        "add-python-regex", help="Add a regex shell Python responder."
    )
    add_python_regex.add_argument("--id", required=True)
    add_python_regex.add_argument("--pattern", required=True)
    add_python_regex.add_argument("--path", required=True)
    add_python_regex.set_defaults(func=_cmd_add_python_regex)

    calls = subcommands.add_parser("calls", help="Inspect recorded calls.")
    call_subcommands = calls.add_subparsers(required=True)
    calls_list = call_subcommands.add_parser("list", help="List recorded calls.")
    calls_list.set_defaults(func=_cmd_calls_list)
    calls_clear = call_subcommands.add_parser("clear", help="Clear recorded calls.")
    calls_clear.set_defaults(func=_cmd_calls_clear)

    plugin_path = subcommands.add_parser("plugin-path", help="Print bundled plugin path.")
    plugin_path.set_defaults(func=_cmd_plugin_path)

    install_global = subcommands.add_parser(
        "install-global",
        help="Install the Codex plugin into global Codex config.",
    )
    install_global.add_argument(
        "--codex-home",
        type=Path,
        default=None,
        help="Codex home directory. Defaults to CODEX_HOME or ~/.codex.",
    )
    install_global.add_argument(
        "--plugin-source",
        type=Path,
        default=None,
        help="Plugin template directory. Defaults to the plugin bundled in this package.",
    )
    install_global.add_argument(
        "--hook-runner",
        choices=["python", "uvx"],
        default="python",
        help="How installed Codex hooks run codex-tool-mocks. Defaults to installer Python.",
    )
    install_global.add_argument(
        "--package-spec",
        default="codex-tool-mocks",
        help="Package spec used when --hook-runner uvx is selected.",
    )
    install_global.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned paths without writing files.",
    )
    install_global.set_defaults(func=_cmd_install_global)
    return parser


def _add_response_args(parser: argparse.ArgumentParser) -> None:
    """Add static response arguments.

    Args:
        parser: Parser to mutate.

    Returns:
        None.
    """
    parser.add_argument("--id", required=True)
    parser.add_argument("--stdout", default="")
    parser.add_argument("--stderr", default="")
    parser.add_argument("--exit-code", type=int, default=0)


def _cmd_init(args: argparse.Namespace) -> None:
    """Handle init.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    root = init_storage(args.root)
    print(root)


def _cmd_add_shell(args: argparse.Namespace) -> None:
    """Handle add-shell.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    _append_fixture(args, {"type": "exact", "command": args.command}, _response(args))


def _cmd_add_shell_regex(args: argparse.Namespace) -> None:
    """Handle add-shell-regex.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    _append_fixture(args, {"type": "regex", "pattern": args.pattern}, _response(args))


def _cmd_add_python(args: argparse.Namespace) -> None:
    """Handle add-python.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    _append_fixture(
        args,
        {"type": "exact", "command": args.command},
        {"type": "python", "path": args.path},
        responder=True,
    )


def _cmd_add_python_regex(args: argparse.Namespace) -> None:
    """Handle add-python-regex.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    _append_fixture(
        args,
        {"type": "regex", "pattern": args.pattern},
        {"type": "python", "path": args.path},
        responder=True,
    )


def _cmd_calls_list(args: argparse.Namespace) -> None:
    """Handle calls list.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    for call in load_calls(args.root):
        print(json.dumps(call, sort_keys=True))


def _cmd_calls_clear(args: argparse.Namespace) -> None:
    """Handle calls clear.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    clear_calls(args.root)


def _cmd_plugin_path(args: argparse.Namespace) -> None:
    """Handle plugin-path.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    print(files("codex_tool_mocks").joinpath("plugin"))


def _cmd_install_global(args: argparse.Namespace) -> None:
    """Handle install-global.

    Args:
        args: Parsed args.

    Returns:
        None.
    """
    result = install_global_plugin(
        codex_home=args.codex_home,
        plugin_source=args.plugin_source,
        hook_runner=args.hook_runner,
        package_spec=args.package_spec,
        dry_run=args.dry_run,
    )
    print(f"Codex home: {result.codex_home}")
    print(f"Installed plugin: {result.installed_plugin_root}")
    print(f"Config: {result.config_path}")
    if args.dry_run:
        print("Dry run only; no files were changed.")
    else:
        print(f"Enabled plugin: {PLUGIN_KEY}")


def _append_fixture(
    args: argparse.Namespace,
    match: dict[str, Any],
    value: dict[str, Any],
    *,
    responder: bool = False,
) -> None:
    """Append a fixture from parsed args.

    Args:
        args: Parsed args.
        match: Match object.
        value: Response or responder object.
        responder: Whether value is a responder config.

    Returns:
        None.
    """
    init_storage(args.root)
    fixture: dict[str, Any] = {"id": args.id, "toolName": "Bash", "match": match}
    if responder:
        fixture["responder"] = value
    else:
        fixture["response"] = value
    append_fixture(fixture, args.root)


def _response(args: argparse.Namespace) -> dict[str, Any]:
    """Build a static response object.

    Args:
        args: Parsed args.

    Returns:
        Response object.
    """
    return {"stdout": args.stdout, "stderr": args.stderr, "exitCode": args.exit_code}


if __name__ == "__main__":
    main()
