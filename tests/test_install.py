import json
import shlex
import sys
import tomllib
from importlib.resources import files
from pathlib import Path

from codex_tool_mocks.cli import main as cli_main
from codex_tool_mocks.install import (
    PLUGIN_KEY,
    build_hook_command,
    ensure_toml_bool,
    install_global_plugin,
)


def test_install_global_plugin_copies_plugin_and_enables_config(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"

    result = install_global_plugin(codex_home=codex_home)

    assert result.installed_plugin_root == (
        codex_home / "plugins" / "cache" / "debug" / "codex-tool-mocks" / "local"
    )
    assert (result.installed_plugin_root / ".codex-plugin" / "plugin.json").is_file()
    config = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert "[features]" in config
    assert "plugins = true" in config
    assert "plugin_hooks = true" in config
    assert f'[plugins."{PLUGIN_KEY}"]' in config
    assert "enabled = true" in config


def test_bundled_plugin_resources_are_packaged() -> None:
    plugin = files("codex_tool_mocks").joinpath("plugin")

    assert plugin.joinpath(".codex-plugin", "plugin.json").is_file()
    assert plugin.joinpath("hooks", "hooks.json").is_file()


def test_install_global_plugin_rewrites_hook_command_to_installer_python(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"

    result = install_global_plugin(codex_home=codex_home)

    hooks = json.loads((result.installed_plugin_root / "hooks" / "hooks.json").read_text())
    pre_hook = hooks["hooks"]["PreToolUse"][0]["hooks"][0]
    assert pre_hook["command"] == f"{shlex.quote(sys.executable)} -m codex_tool_mocks.hook"
    assert "uv run --project" not in pre_hook["command"]


def test_build_hook_command_supports_uvx_runner() -> None:
    command = build_hook_command(hook_runner="uvx", package_spec="codex-tool-mocks")

    assert command == "uvx --from codex-tool-mocks codex-tool-mocks-hook"


def test_install_global_plugin_can_write_uvx_hook_command(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"

    result = install_global_plugin(
        codex_home=codex_home,
        hook_runner="uvx",
        package_spec="codex-tool-mocks",
    )

    hooks = json.loads((result.installed_plugin_root / "hooks" / "hooks.json").read_text())
    pre_hook = hooks["hooks"]["PreToolUse"][0]["hooks"][0]
    assert pre_hook["command"] == "uvx --from codex-tool-mocks codex-tool-mocks-hook"


def test_install_global_plugin_preserves_existing_config(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        "\n".join(
            [
                "[features]",
                "plugins = false",
                "",
                '[plugins."other@debug"]',
                "enabled = false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    install_global_plugin(codex_home=codex_home)

    config = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert "plugins = true" in config
    assert '[plugins."other@debug"]' in config
    assert f'[plugins."{PLUGIN_KEY}"]' in config


def test_install_global_plugin_dry_run_does_not_write(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"

    result = install_global_plugin(codex_home=codex_home, dry_run=True)

    assert result.installed_plugin_root == (
        codex_home / "plugins" / "cache" / "debug" / "codex-tool-mocks" / "local"
    )
    assert not codex_home.exists()


def test_install_global_plugin_is_main_cli_subcommand(
    tmp_path: Path,
    capsys,
) -> None:
    codex_home = tmp_path / "codex-home"

    cli_main(["install-global", "--codex-home", str(codex_home)])

    output = capsys.readouterr().out
    assert "Enabled plugin: codex-tool-mocks@debug" in output
    assert (codex_home / "plugins" / "cache" / "debug" / "codex-tool-mocks" / "local").is_dir()


def test_standalone_install_console_script_is_not_packaged() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    scripts = pyproject["project"]["scripts"]
    assert "codex-tool-mocks" in scripts
    assert "codex-tool-mocks-hook" in scripts
    assert "codex-tool-mocks-install-global" not in scripts


def test_ensure_toml_bool_updates_existing_section() -> None:
    text = "\n".join(["[features]", "plugins = false", "", "[other]", "value = true", ""])

    updated = ensure_toml_bool(text, "features", "plugin_hooks", True)

    assert updated.splitlines() == [
        "[features]",
        "plugins = false",
        "plugin_hooks = true",
        "",
        "[other]",
        "value = true",
    ]
