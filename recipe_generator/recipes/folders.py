"""
レシピフォルダの管理 - レシピフォルダ（投稿素材）からレシピの手がかりを探す

レシピフォルダの中に、料理ごとのフォルダ（フォルダ名＝料理名）を置く。
楽天レシピ自動投稿（Rakutenreshipi_Automation_Edge）の投稿素材と同じフォルダを使う。
"""
from pathlib import Path

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")


def find_recipe_folders(base_folder: Path) -> list[Path]:
    """レシピフォルダの中の料理ごとのフォルダを名前順で返す"""
    base_folder = Path(base_folder)
    if not base_folder.is_dir():
        raise FileNotFoundError(f"レシピフォルダがありません: {base_folder}（.env の RECIPE_FOLDER を確認してください）")
    return sorted(f for f in base_folder.iterdir() if f.is_dir())


def find_images(folder: Path) -> list[Path]:
    """料理の写真（.jpg / .jpeg / .png）を名前順で返す。1枚目をメインの写真にする"""
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES)


def find_reference_text(folder: Path) -> Path | None:
    """以前のツールで作った recipe.txt など（■見出し形式の .txt）を探す"""
    texts = sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".txt")
    return texts[0] if texts else None


def read_text(path: Path) -> str:
    """UTF-8（BOM付きも可）で読み、読めなければ Shift_JIS（メモ帳などで保存した場合）で読む"""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp932")
