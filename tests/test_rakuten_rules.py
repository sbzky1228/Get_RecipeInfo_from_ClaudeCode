from dataclasses import replace

from conftest import sample_answer
from recipe_generator.claude.generate import to_recipe_data
from recipe_generator.rakuten.rules import ingredient_label, rakuten_errors


def recipe(**changes):
    """問題の無いレシピ（changes の項目だけ変える）"""
    return replace(to_recipe_data(sample_answer(), "料理", "main.jpg"), **changes)


def test_no_errors():
    assert rakuten_errors(recipe()) == []


def test_ingredient_label():
    assert ingredient_label("醤油", "A") == "(A)醤油"
    assert ingredient_label("醤油", "") == "醤油"


def test_group_counts_toward_ingredient_name_length():
    base = recipe()
    item = base.ingredients[2]
    item.name = "あ" * 18  # 「(A)」を含めると21文字
    errors = rakuten_errors(base)
    assert len(errors) == 1
    assert "材料名が楽天レシピの上限20文字を超えています（21文字）" in errors[0]


def test_rakuten_title_is_checked():
    errors = rakuten_errors(recipe(platforms={"rakuten": {"title": "あ" * 26}}))
    assert "レシピタイトルが楽天レシピの上限25文字を超えています（26文字）" in errors[0]


def test_emoji_is_rejected():
    errors = rakuten_errors(recipe(description="おいしい😋"))
    assert "絵文字" in errors[0]
