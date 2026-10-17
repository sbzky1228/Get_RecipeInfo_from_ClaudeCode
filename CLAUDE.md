# CLAUDE.md

レシピ自動作成ツール（Python + Claude Code）。`.env` の `RECIPE_FOLDER`（＝楽天レシピ自動投稿 `../Rakutenreshipi_Automation_Edge` の投稿素材）配下の料理名のフォルダのうち recipe.yaml が無いものに、料理名・写真・（あれば）以前の .txt をもとに Claude Code（`claude -p`）でレシピを作ってもらい、`recipe.yaml` を書く。仕様・セットアップは README.md を参照。旧名 `Get_RecipeInfo_from_ChatGPT`（OpenAI API で料理名から recipe.txt を作っていた。フォルダ名・GitHubのリポジトリ名は旧名のまま）。

## 処理の流れとモジュール

起動はプロジェクト直下の `main.py` だけ。本体はパッケージ `recipe_generator/`（`recipes/` 投稿素材フォルダと recipe.yaml、`claude/` Claude Code、`rakuten/` 楽天レシピのルール）。import は `from recipe_generator.xxx import ...` の絶対 import。構成は楽天レシピ自動投稿（`recipe_poster/`）にそろえている。構成図は README の「フォルダ構成」

`main.select_folders`（`recipes.folders.find_recipe_folders`）→ `main.process_folder`（recipe.yaml があればスキップ、`find_images`・`find_reference_text`）→ `claude.generate.generate_recipe`（`claude.prompt.build_prompt` → `claude.client.run_claude` → `to_recipe_data` で `recipes.model.parse_recipe_data` と `rakuten.rules.rakuten_errors`。問題があれば問題点と前回の答えをプロンプトに足して作り直す、最大 `MAX_ATTEMPTS` 回）→ `recipe_yaml_text`（`recipes.model.dump_recipe_yaml`）を書く → `recipes.model.load_recipe_yaml` で読み直して確認

- Claude Code の呼び出し: `--output-format json --json-schema <RECIPE_SCHEMA>` の `structured_output` を使う。`--tools Read` だけ（写真を見るため。書き込みはさせない）、cwd はレシピのフォルダ。`--safe-mode`（個人の CLAUDE.md・プラグイン等を読まない。入れないと毎回15万トークン近い文脈になった）、`--no-session-persistence`。プロンプトは標準入力で渡す。出力は UTF-8
- `--bare` は使わない（OAuth を読まず ANTHROPIC_API_KEY 必須になるため、サブスクリプションで動かなくなる）
- schema_version・dish_name（フォルダ名）・images.main（名前順で最初の写真）はプログラムが入れる。Claude Code には決めさせない
- `recipes/model.py` は `../Rakutenreshipi_Automation_Edge/recipe_poster/recipes/model.py` の**そのままのコピー**（`tests/test_rakuten_project_sync.py` が一致を確認。隣に無い環境ではスキップ）。形式を変えるときは向こうを先に変えてコピーする
- `rakuten/rules.MAX_LENGTHS` は向こうの `rakuten/convert.py` と同じ値（同じテストで確認）。プロンプトと JSON Schema の上限もここから入る
- `config.APP_DIR` は python 実行時は `recipe_generator` の1つ上（プロジェクト直下）、exe 時は exe のフォルダ。`.env`・`logs` はここ。モジュールを移すときはここに注意

## 実行・テスト・ビルド

- 実行: `python -X utf8 main.py [--dry-run] [--limit N] [--folder 名前] [--overwrite]`（コンソールがcp932のため `-X utf8`）
- テスト: `python -X utf8 -m pytest`（Claude Code は呼ばない。`main.main` / `process_folder` / `generate_recipe` の `runner` 引数にフェイクを渡す）
- 静的チェック: `python -m pyflakes main.py recipe_generator tests`、`python -m vulture main.py recipe_generator tests --min-confidence 60`（どちらも指摘ゼロを保つ）
- GitHub Actions: `.github/workflows/tests.yml`（ubuntu、Python 3.12、`.env` 不要）。テストに秘密情報や Claude Code の呼び出しを持ち込まない
- exe: `python -m PyInstaller --noconfirm --clean --workpath "$env:TEMP\RecipeInfo_build" Get_RecipeInfo_from_ClaudeCode.spec` → `dist\Get_RecipeInfo_from_ClaudeCode.exe` をプロジェクト直下へコピー。`dist`・`build` は消してよい。exe は Git に入れない（配布は GitHub Releases）。**コードを変えたら exe を作り直す**（OneDrive配下なので `--workpath` を外に出す）

## 動作確認の注意（重要）

- `.env` の `RECIPE_FOLDER` は本物の投稿素材。そこに recipe.yaml を作ると、楽天レシピ自動投稿は recipe.txt ではなく recipe.yaml を投稿に使う。**本物の投稿素材に書き込む実行はユーザーの許可を取る**。試すときは `--dry-run`、または投稿素材を一時フォルダにコピーして環境変数 `RECIPE_FOLDER`・`LOG_DIR` を指定して実行する（`.env` より環境変数が優先）
- 試験で作ったファイルをユーザーに見せるときは、Temp（AppData は隠しフォルダ）ではなくプロジェクト内など見える場所に置く
- 実際に Claude Code を呼ぶと1件20〜30秒、サブスクリプションの利用枠を使う
- 投稿まで確かめるときは、楽天レシピ自動投稿を `--dry-run` で実行する（入力まで行い下書きを消す）。本番の公開申請はユーザーの許可を取る
- 2026-10-18 時点: 投稿素材の5件すべてに recipe.yaml がある（チャーシューチャーハン・ピーマンのお吸い物和えは楽天側の変換ツールで作成・投稿済み。エッグベネディクト・チョレギサラダ・豚の角煮はこのツールで作成し、楽天レシピ自動投稿の `--dry-run` で入力まで成功、未投稿）

## コーディング規約

- コメント・ログ・ユーザー向けメッセージは日本語
- 失敗理由や分岐結果は `logger.get_logger()` でログファイルに残す
- 不要になった変数・関数・設定は残さない（vulture で確認）
- コミットメッセージは日本語で簡潔に（1行目＋箇条書き数行）
