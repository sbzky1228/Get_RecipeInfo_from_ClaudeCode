import sys
from pathlib import Path

import pytest

# プロジェクト直下の main・recipe_generator を import できるようにする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recipe_generator import logger  # noqa: E402


@pytest.fixture(autouse=True)
def temp_logger(tmp_path, monkeypatch):
    """テスト中のログはプロジェクトの logs ではなく一時フォルダに書く"""
    test_logger = logger.Logger(tmp_path / "logs")
    monkeypatch.setattr(logger, "_shared_logger", test_logger)
    return test_logger


def sample_answer(**changes) -> dict:
    """Claude Code が返す答え（RECIPE_SCHEMA の形）の例"""
    answer = {
        "id": "choregi-salad",
        "title": "ごま油香るチョレギサラダ",
        "description": "シャキシャキの野菜を、ごま油と韓国のりの香りで食べるサラダです。",
        "servings": 2,
        "cook_minutes": 10,
        "cost_yen": 400,
        "tags": ["サラダ", "韓国料理"],
        "meal": ["夕食"],
        "ingredients": [
            {"name": "サニーレタス", "amount": "4枚", "group": ""},
            {"name": "きゅうり", "amount": "1本", "group": ""},
            {"name": "ごま油", "amount": "大さじ1", "group": "A"},
            {"name": "醤油", "amount": "小さじ2", "group": "A"},
        ],
        "steps": [
            {"text": "レタスは食べやすくちぎり、きゅうりは斜め薄切りにする"},
            {"text": "Aを混ぜてドレッシングを作る"},
            {"text": "野菜を器に盛り、食べる直前にドレッシングをかける"},
        ],
        "story": "焼肉屋さんで食べたチョレギサラダをおうちでも食べたくて作りました",
        "tips": "",
    }
    answer.update(changes)
    return answer


@pytest.fixture
def recipe_folder(tmp_path) -> Path:
    """写真が1枚あるレシピフォルダ"""
    folder = tmp_path / "投稿素材" / "チョレギサラダ"
    folder.mkdir(parents=True)
    (folder / "IMG_5740.jpg").write_bytes(b"jpg")
    return folder
