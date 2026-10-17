"""
Claude Code に渡すプロンプトと、答えの形（JSON Schema）

- 料理名（フォルダ名）・写真・以前の .txt を手がかりとして渡す
- 楽天レシピの文字数の上限は rakuten.rules.MAX_LENGTHS から入れる（上限を変えるときはそちらだけ直す）
- schema_version・dish_name・images は Claude Code には決めさせず、プログラムが入れる
"""
import json
from pathlib import Path

from recipe_generator.rakuten.rules import MAX_LENGTHS
from recipe_generator.recipes.model import MEALS

SYSTEM_PROMPT = (
    "あなたは家庭料理が得意な料理研究家で、楽天レシピに投稿するレシピを日本語で書きます。"
    "料理の写真を Read で開いて確かめ、写っている料理として自然で、家庭で再現できるレシピにします。"
    "答えは指定されたJSONの形だけで返します。ファイルの作成・変更はしません。"
)


def _text_schema(max_length: int | None = None) -> dict:
    schema = {"type": "string"}
    if max_length:
        schema["maxLength"] = max_length
    return schema


RECIPE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "title", "description", "servings", "cook_minutes", "cost_yen", "tags", "meal",
                 "ingredients", "steps", "story", "tips"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
        "title": _text_schema(MAX_LENGTHS["レシピタイトル"]),
        "description": _text_schema(MAX_LENGTHS["レシピコメント"]),
        "servings": {"type": "integer", "minimum": 1},
        "cook_minutes": {"type": "integer", "minimum": 1},
        "cost_yen": {"type": "integer", "minimum": 0},
        "tags": {"type": "array", "items": {"type": "string"}},
        "meal": {"type": "array", "items": {"type": "string", "enum": list(MEALS)}},
        "ingredients": {
            "type": "array", "minItems": 1,
            "items": {
                "type": "object", "additionalProperties": False, "required": ["name", "amount", "group"],
                "properties": {"name": _text_schema(MAX_LENGTHS["材料名"]),
                               "amount": _text_schema(MAX_LENGTHS["分量"]),
                               "group": _text_schema()},
            },
        },
        "steps": {
            "type": "array", "minItems": 1,
            "items": {"type": "object", "additionalProperties": False, "required": ["text"],
                      "properties": {"text": _text_schema(MAX_LENGTHS["作り方"])}},
        },
        "story": _text_schema(MAX_LENGTHS["きっかけ"]),
        "tips": _text_schema(MAX_LENGTHS["おいしくなるコツ"]),
    },
}

WRITING_RULES = f"""\
## 各項目の書き方
- title: レシピタイトル。{MAX_LENGTHS["レシピタイトル"]}文字以内。料理の特徴が伝わる名前（料理名そのままでもよい）
- description: レシピコメント。{MAX_LENGTHS["レシピコメント"]}文字以内。どんな味・食感の料理か、どんなときに向くか
- servings: 何人分か（整数）。材料の分量と合わせる。迷ったら2
- cook_minutes: 調理時間（分、整数）。下ごしらえ・漬け込み・冷やす時間も含める
- cost_yen: servings 人分の材料費の目安（円、整数）。調味料は使う分だけで考える
- ingredients: 材料
  - name: 材料名。{MAX_LENGTHS["材料名"]}文字以内（group があると「(A)醤油」のように前に付いた形で数える）
  - amount: 分量。{MAX_LENGTHS["分量"]}文字以内。g・ml・大さじ・小さじ・個・本・枚・少々・適量など日本の家庭の単位で書く（tablespoon などの英語は使わない）
  - group: 合わせ調味料のまとまりなら "A" "B" など。まとまりでなければ空文字 ""
- steps: 作り方。text は1手順{MAX_LENGTHS["作り方"]}文字以内で、番号は付けない。合わせ調味料は「Aを混ぜる」のように group の名前で書く
- story: きっかけ。{MAX_LENGTHS["きっかけ"]}文字以内。作った人の一人称で、このレシピを作った理由として自然な内容
- tips: おいしくなるコツ。{MAX_LENGTHS["おいしくなるコツ"]}文字以内
- tags: 料理のジャンル・種類を表す語を1〜3個（例: 和食, 副菜, サラダ, 丼もの）
- meal: {" / ".join(MEALS)} のうち向いているもの（どれでもなければ空のリスト）
- id: 料理名を英語またはローマ字にし、英小文字・数字・ハイフンでつないだもの（例: chashu-chahan）

## 共通の注意
- 文字数は全角・半角どちらも1文字として数え、上限を必ず守る
- 絵文字（😋 など）は使わない（楽天レシピに入力できない）
- 文章は「です・ます」でも「だ・である」でもよいが、1つのレシピの中でそろえる
"""


def build_prompt(dish_name: str, images: list[Path], reference_text: str | None = None,
                 previous: dict | None = None, problems: list[str] | None = None) -> str:
    """Claude Code に渡すプロンプトを作る（previous / problems は作り直してもらうときの前回の答えと問題点）"""
    lines = [
        f"料理「{dish_name}」のレシピを、楽天レシピに投稿できる形で作ってください。",
        "",
        "## 手がかり",
        f"- 料理名: {dish_name}",
        f"- 料理の写真: {images[0].name}（この作業フォルダにあります。必ず Read で開き、写っている料理・食材・盛り付けに合う内容にしてください）",
    ]
    if len(images) > 1:
        lines.append(f"- ほかの写真: {', '.join(f.name for f in images[1:])}（必要なら Read で開いてください）")
    if reference_text:
        lines += [
            "- 以前作ったこの料理のレシピの文章があります。材料・分量・作り方はできるだけこの内容に合わせ、"
            "文字数の上限や書き方に合わない部分だけ直してください:",
            "```",
            reference_text.strip(),
            "```",
        ]
    lines += ["", WRITING_RULES]
    if problems:
        lines += [
            "## 前回の答えの問題点（必ず直してください）",
            *(f"- {problem}" for problem in problems),
            "",
            "前回の答え:",
            "```json",
            json.dumps(previous, ensure_ascii=False, indent=2),
            "```",
        ]
    return "\n".join(lines)
