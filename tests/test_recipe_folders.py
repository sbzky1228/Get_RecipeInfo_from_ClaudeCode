import pytest

from recipe_generator.recipes.folders import find_images, find_recipe_folders, find_reference_text, read_text


def test_find_recipe_folders_sorted(tmp_path):
    base = tmp_path / "投稿素材"  # tmp_path 直下にはテスト用の logs がある
    for name in ("豚の角煮", "チョレギサラダ"):
        (base / name).mkdir(parents=True)
    (base / "memo.txt").write_text("", encoding="utf-8")
    assert [f.name for f in find_recipe_folders(base)] == ["チョレギサラダ", "豚の角煮"]


def test_find_recipe_folders_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="RECIPE_FOLDER"):
        find_recipe_folders(tmp_path / "無い")


def test_find_images_only_photos_sorted(tmp_path):
    for name in ("b.JPG", "a.png", "recipe.txt", "c.heic"):
        (tmp_path / name).write_bytes(b"")
    assert [f.name for f in find_images(tmp_path)] == ["a.png", "b.JPG"]


def test_find_reference_text(tmp_path):
    assert find_reference_text(tmp_path) is None
    (tmp_path / "レシピ投稿内容.txt").write_text("", encoding="utf-8")
    assert find_reference_text(tmp_path).name == "レシピ投稿内容.txt"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp932"])
def test_read_text_encodings(tmp_path, encoding):
    path = tmp_path / "recipe.txt"
    path.write_text("■レシピタイトル\n豚の角煮", encoding=encoding)
    assert read_text(path) == "■レシピタイトル\n豚の角煮"
