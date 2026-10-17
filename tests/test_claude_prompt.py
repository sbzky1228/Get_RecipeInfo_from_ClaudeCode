from pathlib import Path

from recipe_generator.claude.prompt import RECIPE_SCHEMA, build_prompt


def test_prompt_has_dish_name_and_photo():
    prompt = build_prompt("豚の角煮", [Path("IMG_5848.jpg")])
    assert "料理名: 豚の角煮" in prompt
    assert "料理の写真: IMG_5848.jpg" in prompt
    assert "ほかの写真" not in prompt
    assert "前回の答えの問題点" not in prompt


def test_prompt_lists_other_photos():
    prompt = build_prompt("チョレギサラダ", [Path("a.jpg"), Path("b.jpg")])
    assert "料理の写真: a.jpg" in prompt
    assert "ほかの写真: b.jpg" in prompt


def test_prompt_includes_reference_text():
    prompt = build_prompt("チョレギサラダ", [Path("a.jpg")], "■レシピタイトル\n自家製チョレギサラダ\n")
    assert "自家製チョレギサラダ" in prompt


def test_prompt_includes_problems_and_previous_answer():
    prompt = build_prompt("料理", [Path("a.jpg")], previous={"title": "前回のタイトル"}, problems=["タイトルが長い"])
    assert "- タイトルが長い" in prompt
    assert "前回のタイトル" in prompt


def test_schema_uses_rakuten_limits():
    assert RECIPE_SCHEMA["properties"]["title"]["maxLength"] == 25
    assert RECIPE_SCHEMA["properties"]["steps"]["items"]["properties"]["text"]["maxLength"] == 90
