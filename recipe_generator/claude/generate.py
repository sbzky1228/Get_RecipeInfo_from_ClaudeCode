"""
レシピの作成 - Claude Code の答えを recipe.yaml の内容（RecipeData）にする

- 答えは recipe.yaml の検証（recipes.model.parse_recipe_data）と楽天レシピの文字数チェックを通す。
  問題があれば、その内容と前回の答えを伝えて作り直してもらう（最大 MAX_ATTEMPTS 回）
"""
import datetime
from pathlib import Path
from typing import Callable

from recipe_generator.claude.client import run_claude
from recipe_generator.claude.prompt import RECIPE_SCHEMA, SYSTEM_PROMPT, build_prompt
from recipe_generator.logger import get_logger
from recipe_generator.rakuten.rules import rakuten_errors
from recipe_generator.recipes.model import (
    SCHEMA_VERSION, RecipeData, RecipeFormatError, dump_recipe_yaml, parse_recipe_data,
)

MAX_ATTEMPTS = 3


def to_recipe_data(answer: dict, dish_name: str, main_image: str) -> RecipeData:
    """Claude Code の答えを recipe.yaml と同じ形にして検証する（問題があれば RecipeFormatError）"""
    data = {key: value for key, value in answer.items() if value not in ("", None, [])}
    data["ingredients"] = [{k: v for k, v in item.items() if v != ""} if isinstance(item, dict) else item
                           for item in answer.get("ingredients") or []]
    data.update(schema_version=SCHEMA_VERSION, dish_name=dish_name, images={"main": main_image})
    recipe = parse_recipe_data(data)
    errors = rakuten_errors(recipe)
    if errors:
        raise RecipeFormatError(errors)
    return recipe


def generate_recipe(folder: Path, images: list[Path], reference_text: str | None,
                    runner: Callable[..., dict] = run_claude) -> RecipeData:
    """
    Claude Code にレシピを作ってもらう（フォルダ名を料理名、images[0] をメインの写真にする）。
    MAX_ATTEMPTS 回作り直しても問題が残れば RecipeFormatError
    """
    logger = get_logger()
    previous, problems = None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = build_prompt(folder.name, images, reference_text, previous, problems)
        previous = runner(prompt, RECIPE_SCHEMA, SYSTEM_PROMPT, folder)
        try:
            return to_recipe_data(previous, folder.name, images[0].name)
        except RecipeFormatError as e:
            problems = e.errors
            level = logger.warning if attempt < MAX_ATTEMPTS else logger.error
            level(f"{folder.name}: 答えに問題があります（{attempt}/{MAX_ATTEMPTS}回目）")
            for problem in problems:
                level(f"  - {problem}")
    raise RecipeFormatError(problems or [])


def recipe_yaml_text(recipe: RecipeData) -> str:
    """recipe.yaml の内容（Claude Code で作ったことを先頭のコメントに残す）"""
    today = datetime.date.today().isoformat()
    header = f"# Get_RecipeInfo_from_ClaudeCode で作成（{today}）。投稿前に内容を確認してください\n"
    return header + dump_recipe_yaml(recipe)
