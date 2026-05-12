"""Install codex-tool-mock into the global Codex plugin cache."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

PLUGIN_NAME = "codex-tool-mock"
PYPI_PROJECT_NAME = "codex-tool-mock"
MARKETPLACE_NAME = "debug"
PLUGIN_KEY = f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"


def main(argv: list[str] | None = None) -> None:
    """Run the global plugin installer.

    Args:
        argv: Optional argument vector.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Install codex-tool-mock globally for Codex.")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=None,
        help="Codex home directory. Defaults to CODEX_HOME or ~/.codex.",
    )
    parser.add_argument(
        "--plugin-source",
        type=Path,
        default=None,
        help="Plugin template directory. Defaults to the plugin bundled in this package.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--hook-runner",
        choices=["python", "uvx"],
        default="python",
        help="How installed Codex hooks run codex-tool-mock. Defaults to installer Python.",
    )
    parser.add_argument(
        "--package-spec",
        default=PYPI_PROJECT_NAME,
        help="Package spec used when --hook-runner uvx is selected.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned paths without writing files.",
    )
    args = parser.parse_args(argv)

    result = install_global_plugin(
        codex_home=args.codex_home,
        plugin_source=args.plugin_source,
        project_root=args.project_root,
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


class InstallResult:
    """Result paths from global plugin installation.

    Args:
        codex_home: Codex home directory.
        installed_plugin_root: Installed plugin root.
        config_path: Codex config path.
    """

    def __init__(self, codex_home: Path, installed_plugin_root: Path, config_path: Path) -> None:
        self.codex_home = codex_home
        self.installed_plugin_root = installed_plugin_root
        self.config_path = config_path


def install_global_plugin(
    *,
    codex_home: Path | None = None,
    plugin_source: Path | None = None,
    project_root: Path | None = None,
    hook_runner: str = "python",
    package_spec: str = PYPI_PROJECT_NAME,
    dry_run: bool = False,
) -> InstallResult:
    """Install the plugin into Codex home and enable it in config.toml.

    Args:
        codex_home: Optional Codex home directory.
        plugin_source: Optional plugin template directory.
        project_root: Optional checkout root for old development callers.
        hook_runner: Hook command strategy, either "python" or "uvx".
        package_spec: Package spec to use with the uvx hook runner.
        dry_run: Whether to avoid writing files.

    Returns:
        Installation result paths.
    """
    resolved_home = resolve_codex_home(codex_home)
    source_plugin = resolve_plugin_source(plugin_source, project_root)
    if not source_plugin.joinpath(".codex-plugin", "plugin.json").is_file():
        raise FileNotFoundError(f"missing plugin manifest under {source_plugin}")
    hook_command = build_hook_command(hook_runner=hook_runner, package_spec=package_spec)

    installed_root = resolved_home / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME / "local"
    config_path = resolved_home / "config.toml"
    result = InstallResult(
        codex_home=resolved_home,
        installed_plugin_root=installed_root,
        config_path=config_path,
    )
    if dry_run:
        return result

    install_plugin_files(source_plugin, installed_root, hook_command)
    update_codex_config(config_path)
    return result


def resolve_codex_home(codex_home: Path | None = None) -> Path:
    """Resolve Codex home.

    Args:
        codex_home: Optional explicit Codex home.

    Returns:
        Absolute Codex home path.
    """
    if codex_home is not None:
        return codex_home.expanduser().resolve()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def resolve_plugin_source(
    plugin_source: Path | None = None,
    project_root: Path | None = None,
) -> Traversable:
    """Resolve the plugin template source.

    Args:
        plugin_source: Optional explicit plugin template directory.
        project_root: Optional checkout root for old development callers.

    Returns:
        Plugin template source.
    """
    if plugin_source is not None:
        return plugin_source.expanduser().resolve()
    if project_root is not None:
        return project_root.expanduser().resolve() / "plugin"
    return files("codex_tool_mock").joinpath("plugin")


def build_hook_command(
    *,
    hook_runner: str = "python",
    package_spec: str = PLUGIN_NAME,
    python_executable: str | Path | None = None,
) -> str:
    """Build the command Codex should run for plugin hooks.

    Args:
        hook_runner: Hook runner strategy, either "python" or "uvx".
        package_spec: Package spec for uvx.
        python_executable: Optional Python executable override.

    Returns:
        Hook command string.
    """
    if hook_runner == "python":
        executable = str(python_executable or sys.executable)
        return f"{shlex.quote(executable)} -m codex_tool_mock.hook"
    if hook_runner == "uvx":
        return f"uvx --from {shlex.quote(package_spec)} codex-tool-mock-hook"
    raise ValueError(f"unsupported hook runner: {hook_runner}")


def install_plugin_files(
    source_plugin: Traversable,
    installed_root: Path,
    hook_command: str,
) -> None:
    """Copy plugin files and rewrite hook commands for global installation.

    Args:
        source_plugin: Source plugin directory.
        installed_root: Target Codex plugin root.
        hook_command: Command to write into command hooks.

    Returns:
        None.
    """
    if installed_root.exists():
        shutil.rmtree(installed_root)
    copy_resource_tree(source_plugin, installed_root)
    hooks_path = installed_root / "hooks" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    rewrite_hook_commands(hooks, hook_command)
    hooks_path.write_text(json.dumps(hooks, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copy_resource_tree(source: Traversable, target: Path) -> None:
    """Copy a Traversable resource tree to a filesystem path.

    Args:
        source: Source resource directory.
        target: Target filesystem directory.

    Returns:
        None.
    """
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        child_target = target / child.name
        if child.is_dir():
            copy_resource_tree(child, child_target)
        else:
            child_target.write_bytes(child.read_bytes())


def rewrite_hook_commands(hooks: dict[str, Any], hook_command: str) -> None:
    """Rewrite bundled command hooks to use the selected hook command.

    Args:
        hooks: Parsed hooks.json object.
        hook_command: Hook command string.

    Returns:
        None.
    """
    events = hooks.get("hooks", {})
    if not isinstance(events, dict):
        return
    for groups in events.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                if isinstance(hook, dict) and hook.get("type") == "command":
                    hook["command"] = hook_command


def update_codex_config(config_path: Path) -> None:
    """Enable plugins, plugin hooks, and this plugin in Codex config.

    Args:
        config_path: Codex config.toml path.

    Returns:
        None.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    text = ensure_toml_bool(text, "features", "plugins", True)
    text = ensure_toml_bool(text, "features", "plugin_hooks", True)
    text = ensure_toml_bool(text, f'plugins."{PLUGIN_KEY}"', "enabled", True)
    config_path.write_text(text, encoding="utf-8")


def ensure_toml_bool(text: str, section: str, key: str, value: bool) -> str:
    """Ensure a boolean key exists in a simple TOML section.

    Args:
        text: Existing TOML text.
        section: Section name without brackets.
        key: Key to set.
        value: Boolean value.

    Returns:
        Updated TOML text.
    """
    desired = "true" if value else "false"
    lines = text.splitlines()
    header = f"[{section}]"
    section_start = find_section(lines, header)
    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([header, f"{key} = {desired}"])
        return "\n".join(lines) + "\n"

    section_end = find_section_end(lines, section_start + 1)
    for index in range(section_start + 1, section_end):
        stripped = lines[index].strip()
        if stripped.startswith(f"{key} ") or stripped.startswith(f"{key}="):
            lines[index] = f"{key} = {desired}"
            return "\n".join(lines) + "\n"

    lines.insert(section_end, f"{key} = {desired}")
    return "\n".join(lines) + "\n"


def find_section(lines: list[str], header: str) -> int | None:
    """Find a TOML section header.

    Args:
        lines: TOML lines.
        header: Exact section header.

    Returns:
        Section line index, or None.
    """
    for index, line in enumerate(lines):
        if line.strip() == header:
            return index
    return None


def find_section_end(lines: list[str], start: int) -> int:
    """Find the end index for a TOML section.

    Args:
        lines: TOML lines.
        start: First line after the section header.

    Returns:
        Section end insertion index.
    """
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            insert_at = index
            while insert_at > start and not lines[insert_at - 1].strip():
                insert_at -= 1
            return insert_at
    return len(lines)


if __name__ == "__main__":
    main()
