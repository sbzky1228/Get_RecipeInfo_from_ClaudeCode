import json

import pytest

from recipe_generator import config
from recipe_generator.claude import client
from recipe_generator.claude.client import ClaudeCodeError, build_command, parse_output


def test_parse_output_returns_structured_output():
    stdout = json.dumps({"type": "result", "subtype": "success", "is_error": False,
                         "result": "{}", "structured_output": {"title": "卵焼き"}}, ensure_ascii=False)
    assert parse_output(stdout) == {"title": "卵焼き"}


@pytest.mark.parametrize("stdout", [
    "Not logged in",
    json.dumps({"subtype": "success", "is_error": True, "result": "Invalid API key"}),
    json.dumps({"subtype": "error_max_turns", "is_error": False}),
    json.dumps({"subtype": "success", "is_error": False, "result": "卵焼きです"}),
])
def test_parse_output_errors(stdout):
    with pytest.raises(ClaudeCodeError):
        parse_output(stdout)


def test_command_allows_only_read(monkeypatch):
    monkeypatch.setattr(config, "CLAUDE_MODEL", "sonnet")
    command = build_command("claude", {"type": "object"}, "システム")
    assert command[command.index("--tools") + 1] == "Read"
    assert command[command.index("--model") + 1] == "sonnet"
    assert "--safe-mode" in command


def test_find_claude_from_setting(tmp_path, monkeypatch):
    exe = tmp_path / "claude.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(config, "CLAUDE_PATH", str(exe))
    assert client.find_claude() == str(exe)


def test_find_claude_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLAUDE_PATH", "")
    monkeypatch.setattr(client.shutil, "which", lambda name: None)
    monkeypatch.setattr(client.Path, "home", lambda: tmp_path)
    with pytest.raises(ClaudeCodeError, match="見つかりません"):
        client.find_claude()
