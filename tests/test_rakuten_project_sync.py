"""
楽天レシピ自動投稿（Rakutenreshipi_Automation_Edge）と recipe.yaml の形式・文字数の上限がそろっているかの確認。
隣のフォルダに楽天レシピ自動投稿が無い環境（GitHub Actions など）では行わない。
"""
import ast
from pathlib import Path

import pytest

from recipe_generator.rakuten import rules

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAKUTEN_DIR = PROJECT_DIR.parent / "Rakutenreshipi_Automation_Edge" / "recipe_poster"

if not RAKUTEN_DIR.is_dir():
    pytest.skip("楽天レシピ自動投稿のフォルダが隣に無い", allow_module_level=True)


def test_model_is_same_as_rakuten_project():
    ours = (PROJECT_DIR / "recipe_generator" / "recipes" / "model.py").read_text(encoding="utf-8")
    theirs = (RAKUTEN_DIR / "recipes" / "model.py").read_text(encoding="utf-8")
    assert ours == theirs, "recipe_poster/recipes/model.py が変わっています。recipe_generator/recipes/model.py にコピーしてください"


def test_max_lengths_match_rakuten_project():
    tree = ast.parse((RAKUTEN_DIR / "rakuten" / "convert.py").read_text(encoding="utf-8"))
    theirs = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "MAX_LENGTHS")
    for name, limit in rules.MAX_LENGTHS.items():
        assert theirs[name] == limit, f"{name} の上限が楽天レシピ自動投稿と違います"
