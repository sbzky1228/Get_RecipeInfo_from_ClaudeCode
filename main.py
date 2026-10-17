"""
レシピ自動作成（Get_RecipeInfo_from_ClaudeCode） - メイン

1. レシピフォルダ（.env の RECIPE_FOLDER）の中の、料理名のフォルダのうち recipe.yaml が無いものを選ぶ
2. フォルダの写真（と、あれば以前の .txt）をもとに Claude Code にレシピを作ってもらう
   （内容に問題があれば作り直してもらう）
3. recipe.yaml を書き、楽天レシピ自動投稿（Rakutenreshipi_Automation_Edge）と同じ検証で読み直して確かめる

使い方:
    python main.py                      recipe.yaml が無いフォルダすべてに作る
    python main.py --folder 豚の角煮     指定したフォルダだけ（複数指定可）
    python main.py --limit 1            1件だけ作る
    python main.py --overwrite          既にある recipe.yaml も作り直す
    python main.py --dry-run            作った内容をログに出すだけで、recipe.yaml は書かない
"""
import argparse
import sys
from pathlib import Path
from typing import Callable

from recipe_generator import config
from recipe_generator.claude.client import ClaudeCodeError, run_claude
from recipe_generator.claude.generate import MAX_ATTEMPTS, generate_recipe, recipe_yaml_text
from recipe_generator.logger import get_logger
from recipe_generator.recipes.folders import (
    IMAGE_SUFFIXES, find_images, find_recipe_folders, find_reference_text, read_text,
)
from recipe_generator.recipes.model import RECIPE_FILE_NAME, RecipeFormatError, load_recipe_yaml

# 1フォルダの処理結果
CREATED, SKIPPED, FAILED = "作成", "スキップ", "要確認"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="写真から Claude Code にレシピを作ってもらい、recipe.yaml を作ります")
    parser.add_argument("--limit", type=int, default=None, help="作る件数の上限")
    parser.add_argument("--folder", action="append", default=None, metavar="フォルダ名",
                        help="指定したフォルダだけ作る（複数指定可）")
    parser.add_argument("--overwrite", action="store_true", help=f"既にある {RECIPE_FILE_NAME} も作り直す")
    parser.add_argument("--dry-run", action="store_true",
                        help=f"作った内容をログに出すだけで {RECIPE_FILE_NAME} は書かない")
    return parser.parse_args(argv)


def select_folders(base_folder: Path, names: list[str] | None) -> list[Path]:
    """対象のフォルダ（--folder の指定が無ければすべて）を返す。指定したフォルダが無ければ FileNotFoundError"""
    folders = find_recipe_folders(base_folder)
    if not names:
        return folders
    by_name = {folder.name: folder for folder in folders}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise FileNotFoundError(f"指定したフォルダがありません: {', '.join(missing)}")
    return [by_name[name] for name in names]


def process_folder(folder: Path, overwrite: bool = False, dry_run: bool = False,
                   runner: Callable[..., dict] = run_claude) -> str:
    """1つのフォルダに recipe.yaml を作る。結果（CREATED / SKIPPED / FAILED）を返す"""
    logger = get_logger()
    yaml_path = folder / RECIPE_FILE_NAME
    if yaml_path.exists() and not overwrite:
        logger.info(f"{folder.name}: {RECIPE_FILE_NAME} が既にあるためスキップします（作り直す場合は --overwrite）")
        return SKIPPED

    images = find_images(folder)
    if not images:
        logger.error(f"{folder.name}: 写真（{' / '.join(IMAGE_SUFFIXES)}）が無いため作れません")
        return FAILED
    if len(images) > 1:
        logger.warning(f"{folder.name}: 写真が複数あるため {images[0].name} をメインの写真にします")

    reference = find_reference_text(folder)
    reference_text = None
    if reference:
        try:
            reference_text = read_text(reference)
            logger.info(f"{folder.name}: {reference.name} の内容をもとに作ります")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"{folder.name}: {reference.name} を読み込めないため写真だけで作ります: {e}")

    logger.info(f"{folder.name}: Claude Code でレシピを作っています（写真: {images[0].name}）")
    try:
        recipe = generate_recipe(folder, images, reference_text, runner)
    except ClaudeCodeError as e:
        logger.error(f"{folder.name}: {e}")
        return FAILED
    except RecipeFormatError:
        logger.error(f"{folder.name}: {MAX_ATTEMPTS}回作り直しても問題が残ったため {RECIPE_FILE_NAME} を作りませんでした")
        return FAILED

    content = recipe_yaml_text(recipe)
    if dry_run:
        logger.info(f"{folder.name}: [お試し] 次の内容になります（{RECIPE_FILE_NAME} は作りません）\n{content}")
        return CREATED

    yaml_path.write_text(content, encoding="utf-8")
    try:
        load_recipe_yaml(yaml_path)  # 楽天レシピ自動投稿と同じ読み込み・検証を通るか確かめる
    except RecipeFormatError as e:
        logger.error(f"{folder.name}: 作った {RECIPE_FILE_NAME} の読み込みで問題が見つかりました。内容を直してください")
        for error in e.errors:
            logger.error(f"  - {error}")
        return FAILED
    logger.info(f"{folder.name}: {RECIPE_FILE_NAME} を作りました（タイトル: {recipe.title}）")
    return CREATED


def main(argv: list[str] | None = None, runner: Callable[..., dict] = run_claude) -> int:
    """終了コード: すべて成功（または対象なし）なら 0、作れなかったフォルダがあれば 1"""
    args = parse_args(argv)
    logger = get_logger()
    if not config.RECIPE_FOLDER:
        logger.error(".env に RECIPE_FOLDER（レシピフォルダの場所）を設定してください")
        return 1
    try:
        folders = select_folders(Path(config.RECIPE_FOLDER), args.folder)
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    results = []
    for folder in folders:
        if args.limit is not None and results.count(CREATED) + results.count(FAILED) >= args.limit:
            break
        results.append(process_folder(folder, args.overwrite, args.dry_run, runner))

    logger.info(f"終了しました: 作成 {results.count(CREATED)}件 / スキップ {results.count(SKIPPED)}件 / "
                f"要確認 {results.count(FAILED)}件")
    logger.info(f"ログ: {logger.log_file}")
    return 1 if FAILED in results else 0


if __name__ == "__main__":
    sys.exit(main())
