"""main（対象フォルダの選択・1フォルダの処理・集計）のテスト。Claude Code の代わりに FakeRunner を使う"""
from conftest import sample_answer
import main
from recipe_generator import config
from recipe_generator.recipes.model import load_recipe_yaml


class FakeRunner:
    """Claude Code の代わりに、決めておいた答えを返す（answers が尽きたら sample_answer）"""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt, schema, system_prompt, cwd):
        self.prompts.append(prompt)
        return self.answers.pop(0) if self.answers else sample_answer()


def make_folders(tmp_path, *names):
    """写真入りのフォルダを作り、RECIPE_FOLDER にするフォルダを返す（tmp_path 直下の logs と分ける）"""
    base = tmp_path / "投稿素材"
    base.mkdir()
    for name in names:
        (base / name).mkdir()
        (base / name / "main.jpg").write_bytes(b"jpg")
    return base


# ------------------------------------------------------------
# process_folder（1フォルダの処理）
# ------------------------------------------------------------
def test_creates_recipe_yaml_that_loads(recipe_folder):
    runner = FakeRunner()
    assert main.process_folder(recipe_folder, runner=runner) == main.CREATED
    recipe = load_recipe_yaml(recipe_folder / "recipe.yaml")
    assert recipe.title == "ごま油香るチョレギサラダ"
    assert recipe.dish_name == "チョレギサラダ"
    assert recipe.main_image == "IMG_5740.jpg"
    assert "IMG_5740.jpg" in runner.prompts[0]


def test_skips_existing_yaml(recipe_folder):
    (recipe_folder / "recipe.yaml").write_text("既存", encoding="utf-8")
    runner = FakeRunner()
    assert main.process_folder(recipe_folder, runner=runner) == main.SKIPPED
    assert (recipe_folder / "recipe.yaml").read_text(encoding="utf-8") == "既存"
    assert runner.prompts == []


def test_overwrite_existing_yaml(recipe_folder):
    (recipe_folder / "recipe.yaml").write_text("既存", encoding="utf-8")
    assert main.process_folder(recipe_folder, overwrite=True, runner=FakeRunner()) == main.CREATED
    assert load_recipe_yaml(recipe_folder / "recipe.yaml").title == "ごま油香るチョレギサラダ"


def test_dry_run_does_not_write(recipe_folder):
    assert main.process_folder(recipe_folder, dry_run=True, runner=FakeRunner()) == main.CREATED
    assert not (recipe_folder / "recipe.yaml").exists()


def test_folder_without_photo_fails(tmp_path):
    folder = tmp_path / "写真なし"
    folder.mkdir()
    runner = FakeRunner()
    assert main.process_folder(folder, runner=runner) == main.FAILED
    assert runner.prompts == []


def test_reference_text_is_used(recipe_folder):
    (recipe_folder / "recipe.txt").write_text("■レシピタイトル\n自家製チョレギサラダ\n", encoding="cp932")
    runner = FakeRunner()
    assert main.process_folder(recipe_folder, runner=runner) == main.CREATED
    assert "自家製チョレギサラダ" in runner.prompts[0]


def test_gives_up_and_writes_nothing(recipe_folder):
    runner = FakeRunner(*[sample_answer(story="")] * 3)
    assert main.process_folder(recipe_folder, runner=runner) == main.FAILED
    assert not (recipe_folder / "recipe.yaml").exists()


# ------------------------------------------------------------
# main（全体）
# ------------------------------------------------------------
def test_creates_only_missing(tmp_path, monkeypatch):
    base = make_folders(tmp_path, "チョレギサラダ", "豚の角煮")
    (base / "豚の角煮" / "recipe.yaml").write_text("既存", encoding="utf-8")
    monkeypatch.setattr(config, "RECIPE_FOLDER", str(base))
    assert main.main([], runner=FakeRunner()) == 0
    assert (base / "チョレギサラダ" / "recipe.yaml").exists()
    assert (base / "豚の角煮" / "recipe.yaml").read_text(encoding="utf-8") == "既存"


def test_limit_counts_only_created(tmp_path, monkeypatch):
    base = make_folders(tmp_path, "a", "b", "c")
    (base / "a" / "recipe.yaml").write_text("既存", encoding="utf-8")
    monkeypatch.setattr(config, "RECIPE_FOLDER", str(base))
    assert main.main(["--limit", "1"], runner=FakeRunner()) == 0
    assert (base / "b" / "recipe.yaml").exists()
    assert not (base / "c" / "recipe.yaml").exists()


def test_folder_option(tmp_path, monkeypatch):
    base = make_folders(tmp_path, "a", "b")
    monkeypatch.setattr(config, "RECIPE_FOLDER", str(base))
    assert main.main(["--folder", "b"], runner=FakeRunner()) == 0
    assert not (base / "a" / "recipe.yaml").exists()
    assert (base / "b" / "recipe.yaml").exists()


def test_missing_folder_option(tmp_path, monkeypatch):
    base = make_folders(tmp_path, "a")
    monkeypatch.setattr(config, "RECIPE_FOLDER", str(base))
    assert main.main(["--folder", "無い"], runner=FakeRunner()) == 1


def test_failure_returns_1_and_logs_reason(tmp_path, monkeypatch, temp_logger):
    base = make_folders(tmp_path)
    (base / "写真なし").mkdir()
    monkeypatch.setattr(config, "RECIPE_FOLDER", str(base))
    assert main.main([], runner=FakeRunner()) == 1
    assert "写真なし: 写真" in temp_logger.log_file.read_text(encoding="utf-8")


def test_recipe_folder_not_set(monkeypatch):
    monkeypatch.setattr(config, "RECIPE_FOLDER", "")
    assert main.main([], runner=FakeRunner()) == 1
