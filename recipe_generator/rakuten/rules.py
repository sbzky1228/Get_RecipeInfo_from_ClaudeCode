"""
楽天レシピの入力ルール - 作った recipe.yaml がそのまま楽天レシピに投稿できるかを確かめる

上限文字数などは Rakutenreshipi_Automation_Edge の recipe_poster/rakuten/convert.py と同じ。
楽天レシピ側の上限が変わったら両方をそろえる。
"""
from recipe_generator.recipes.model import RecipeData

# 楽天レシピの入力欄の上限文字数（投稿画面の data-maxlength）
MAX_LENGTHS = {
    "レシピタイトル": 25,
    "レシピコメント": 80,
    "きっかけ": 120,
    "おいしくなるコツ": 120,
    "材料名": 20,
    "分量": 20,
    "作り方": 90,
}


def ingredient_label(name: str, group: str) -> str:
    """楽天レシピに入力される材料名（group があれば「(A)醤油」のように前に付く）"""
    return f"({group}){name}" if group else name


def rakuten_errors(recipe: RecipeData) -> list[str]:
    """楽天レシピに投稿できない内容（文字数超過・絵文字）を日本語のメッセージで返す。問題が無ければ空リスト"""
    errors = []

    def check_length(name: str, value: str):
        if len(value) > MAX_LENGTHS[name]:
            errors.append(f"{name}が楽天レシピの上限{MAX_LENGTHS[name]}文字を超えています（{len(value)}文字）: {value}")

    title = recipe.platforms.get("rakuten", {}).get("title") or recipe.title
    check_length("レシピタイトル", title)
    check_length("レシピコメント", recipe.description)
    check_length("きっかけ", recipe.story)
    check_length("おいしくなるコツ", recipe.tips)
    for item in recipe.ingredients:
        check_length("材料名", ingredient_label(item.name, item.group))
        check_length("分量", item.amount)
    for step in recipe.steps:
        check_length("作り方", step.text)

    # Edge WebDriver は絵文字など一部の文字（U+10000以降）を入力できない
    all_text = "".join([title, recipe.description, recipe.story, recipe.tips, recipe.dish_name,
                        *(step.text for step in recipe.steps),
                        *(item.name + item.amount + item.group for item in recipe.ingredients)])
    unsupported = sorted({ch for ch in all_text if ord(ch) > 0xFFFF})
    if unsupported:
        errors.append(f"楽天レシピに入力できない文字（絵文字など）が含まれています: {' '.join(unsupported)}")
    return errors
