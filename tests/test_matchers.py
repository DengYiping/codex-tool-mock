import pytest

from codex_tool_mock.matchers import FixtureMatchError, find_matching_fixture


def test_exact_match_wins_by_file_order() -> None:
    fixtures = [
        {
            "id": "exact",
            "toolName": "Bash",
            "match": {"type": "exact", "command": "git status"},
            "response": {"stdout": "exact", "stderr": "", "exitCode": 0},
        },
        {
            "id": "regex",
            "toolName": "Bash",
            "match": {"type": "regex", "pattern": "^git status"},
            "response": {"stdout": "regex", "stderr": "", "exitCode": 0},
        },
    ]

    match = find_matching_fixture("Bash", "git status", fixtures)

    assert match is not None
    assert match.fixture["id"] == "exact"


def test_regex_match_supports_shell_commands() -> None:
    fixtures = [
        {
            "id": "status",
            "toolName": "Bash",
            "match": {"type": "regex", "pattern": r"^git status( --short)?$"},
            "response": {"stdout": "", "stderr": "", "exitCode": 0},
        }
    ]

    assert find_matching_fixture("Bash", "git status", fixtures) is not None
    assert find_matching_fixture("Bash", "git status --short", fixtures) is not None
    assert find_matching_fixture("Bash", "git diff", fixtures) is None


def test_invalid_regex_raises_clear_error() -> None:
    fixtures = [
        {
            "id": "bad",
            "toolName": "Bash",
            "match": {"type": "regex", "pattern": "["},
            "response": {"stdout": "", "stderr": "", "exitCode": 0},
        }
    ]

    with pytest.raises(FixtureMatchError, match="invalid regex"):
        find_matching_fixture("Bash", "git status", fixtures)
