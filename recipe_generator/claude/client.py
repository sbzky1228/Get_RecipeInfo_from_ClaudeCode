"""
Claude Code の呼び出し - claude -p（非対話モード）でレシピを作ってもらい、JSONで受け取る

- Claude Code にログイン済みのアカウント（Pro / Max などのサブスクリプション）で動く。APIキーは不要
  （環境変数 ANTHROPIC_API_KEY が設定されている場合は、そのAPIキーで従量課金になる）
- 使えるツールは Read だけにし、レシピフォルダの写真を見て内容を決めてもらう（ファイルの書き込みはさせない）
- 出力は --json-schema で形を決め、structured_output として受け取る
"""
import json
import shutil
import subprocess
from pathlib import Path

from recipe_generator import config


class ClaudeCodeError(RuntimeError):
    """Claude Code を起動できない・失敗した・期待した形で答えなかった"""


def find_claude() -> str:
    """claude の実行ファイルを探す（.env の CLAUDE_PATH → PATH → 既定のインストール先）"""
    candidates = [config.CLAUDE_PATH, shutil.which("claude"),
                  str(Path.home() / ".local" / "bin" / "claude.exe"), str(Path.home() / ".local" / "bin" / "claude")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise ClaudeCodeError(
        "Claude Code（claude）が見つかりません。Claude Code をインストールして一度 claude でログインするか、"
        ".env の CLAUDE_PATH に claude.exe の場所を書いてください"
    )


def build_command(claude: str, schema: dict, system_prompt: str) -> list[str]:
    command = [
        claude, "-p",
        "--output-format", "json",
        "--json-schema", json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
        "--system-prompt", system_prompt,
        "--tools", "Read",
        "--allowedTools", "Read",
        # 個人の CLAUDE.md・プラグイン・MCP などを読み込まない（毎回同じ条件で、余計な文脈を使わない）
        "--safe-mode",
        "--no-session-persistence",
    ]
    if config.CLAUDE_MODEL:
        command += ["--model", config.CLAUDE_MODEL]
    return command


def parse_output(stdout: str) -> dict:
    """claude -p --output-format json の出力から structured_output を取り出す"""
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise ClaudeCodeError(f"Claude Code の出力を読み取れません: {stdout.strip()[:300]}") from e
    if not isinstance(result, dict):
        raise ClaudeCodeError(f"Claude Code の出力が想定と違います: {stdout.strip()[:300]}")
    if result.get("is_error") or result.get("subtype") != "success":
        raise ClaudeCodeError(f"Claude Code がエラーを返しました: {str(result.get('result', ''))[:300]}")
    output = result.get("structured_output")
    if not isinstance(output, dict):
        raise ClaudeCodeError("Claude Code が指定した形（JSON）で答えませんでした")
    return output


def run_claude(prompt: str, schema: dict, system_prompt: str, cwd: Path) -> dict:
    """
    cwd（レシピフォルダ）で Claude Code を実行し、schema の形の答えを辞書で返す。
    プロンプトは長い日本語になるため、コマンドライン引数ではなく標準入力で渡す。
    """
    command = build_command(find_claude(), schema, system_prompt)
    try:
        completed = subprocess.run(
            command, input=prompt, cwd=cwd, capture_output=True,
            encoding="utf-8", errors="replace", timeout=config.CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeCodeError(f"Claude Code が{config.CLAUDE_TIMEOUT}秒以内に終わりませんでした"
                              "（.env の CLAUDE_TIMEOUT で延ばせます）") from e
    except OSError as e:
        raise ClaudeCodeError(f"Claude Code を起動できません: {e}") from e
    if completed.returncode != 0 and not completed.stdout.strip():
        detail = (completed.stderr or "").strip()[:300]
        raise ClaudeCodeError(f"Claude Code が異常終了しました（終了コード {completed.returncode}）: {detail}")
    return parse_output(completed.stdout)
