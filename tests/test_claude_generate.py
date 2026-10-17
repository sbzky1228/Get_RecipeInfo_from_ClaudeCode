import pytest

from conftest import sample_answer
from recipe_generator.claude.generate import MAX_ATTEMPTS, generate_recipe, recipe_yaml_text, to_recipe_data
from recipe_generator.recipes.model import RecipeFormatError, parse_recipe_data

import yaml


class FakeRunner:
    """Claude Code の代わりに、決めておいた答えを順に返す"""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt, schema, system_prompt, cwd):
        self.prompts.append(prompt)
        return self.answers.pop(0)


def test_to_recipe_data_fills_program_fields():
    recipe = to_recipe_data(sample_answer(), "チョレギサラダ", "IMG_5740.jpg")
    assert recipe.dish_name == "チョレギサラダ"
    assert recipe.main_image == "IMG_5740.jpg"
    assert recipe.ingredients[0].group == ""     # 空文字の group は書かない
    assert recipe.ingredients[2].group == "A"
    assert recipe.tips == ""


def test_to_recipe_data_rejects_missing_required():
    with pytest.raises(RecipeFormatError) as e:
        to_recipe_data(sample_answer(story=""), "料理", "main.jpg")
    assert any("story" in error for error in e.value.errors)


def test_generate_retries_with_problems(recipe_folder):
    too_long = sample_answer(title="とても長いタイトルのチョレギサラダ（ごま油と韓国のりの香り）")
    runner = FakeRunner(too_long, sample_answer())
    recipe = generate_recipe(recipe_folder, [recipe_folder / "IMG_5740.jpg"], None, runner)
    assert recipe.title == "ごま油香るチョレギサラダ"
    assert len(runner.prompts) == 2
    assert "前回の答えの問題点" in runner.prompts[1]
    assert "レシピタイトルが楽天レシピの上限25文字を超えています" in runner.prompts[1]


def test_generate_gives_up_after_max_attempts(recipe_folder):
    runner = FakeRunner(*[sample_answer(story="")] * MAX_ATTEMPTS)
    with pytest.raises(RecipeFormatError):
        generate_recipe(recipe_folder, [recipe_folder / "IMG_5740.jpg"], None, runner)
    assert len(runner.prompts) == MAX_ATTEMPTS


def test_recipe_yaml_text_round_trip():
    recipe = to_recipe_data(sample_answer(), "チョレギサラダ", "IMG_5740.jpg")
    text = recipe_yaml_text(recipe)
    assert text.startswith("# Get_RecipeInfo_from_ClaudeCode で作成")
    assert parse_recipe_data(yaml.safe_load(text)) == recipe
