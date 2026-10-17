"""
設定ファイル - .env の読み込みと定数の管理

- レシピフォルダ（投稿素材）
- Claude Code の実行設定
- ログの保存先
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# プログラムのフォルダ（.env・logsの基準）
# - .exe実行時: Get_RecipeInfo_from_ClaudeCode.exe と同じフォルダ
# - python main.py 実行時: プロジェクト直下（このファイルは recipe_generator フォルダの中にある）
# タスクスケジューラ等で作業フォルダが変わっても同じ場所を使うよう固定する
APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, 'frozen', False)
    else Path(__file__).resolve().parent.parent
)

# プログラムのフォルダの .env を優先し、無ければ作業フォルダの .env を読む
_dotenv_file = APP_DIR / '.env'
load_dotenv(_dotenv_file if _dotenv_file.exists() else Path.cwd() / '.env')


def _env(name: str) -> str:
    return os.getenv(name, '').strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    return int(value) if value.isdigit() else default


def _env_path(name: str, default: Path) -> Path:
    """フォルダの設定（相対パスはプログラムのフォルダ基準。未指定なら default）"""
    value = _env(name)
    return (APP_DIR / value).resolve() if value else default


# ============================================================
# レシピフォルダ
# 楽天レシピ自動投稿（Rakutenreshipi_Automation_Edge）の base_folder_path と同じフォルダを指定する
# ============================================================
RECIPE_FOLDER = _env('RECIPE_FOLDER')

# ============================================================
# Claude Code
# ============================================================
# claude（claude.exe）の場所。未指定なら PATH と既定のインストール先から探す
CLAUDE_PATH = _env('CLAUDE_PATH')
# 使うモデル（例: sonnet / opus）。未指定なら Claude Code の既定のモデル
CLAUDE_MODEL = _env('CLAUDE_MODEL')
# 1レシピあたりの待ち時間の上限（秒）
CLAUDE_TIMEOUT = _env_int('CLAUDE_TIMEOUT', 300)

# ============================================================
# ログの保存先（相対パスはプログラムのフォルダ基準。未指定ならプログラムのフォルダの logs）
# ============================================================
LOG_DIR = _env_path('LOG_DIR', APP_DIR / 'logs')
