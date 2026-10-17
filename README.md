# レシピ自動作成（Claude Code）

投稿素材フォルダに置いた料理写真を Claude Code に見てもらい、レシピを作って `recipe.yaml` に保存するツールです。
`recipe.yaml` は [楽天レシピ自動投稿（Rakutenreshipi_Automation_Edge）](https://github.com/sbzky1228/sbzky1228-Rakutenreshipi_Automation_Edge) がそのまま読み込める形式で、
楽天レシピの文字数の上限などを守った内容になります。

[![テスト](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

以前の名前は `Get_RecipeInfo_from_ChatGPT`（ChatGPT の API で料理名から recipe.txt を作るツール）でした。

## できること

- 投稿素材フォルダ（`.env` の `RECIPE_FOLDER`）の中の、料理名のフォルダのうち `recipe.yaml` が無いものに `recipe.yaml` を作る
- レシピは次の手がかりから作る
  1. **料理名**（フォルダ名）: 何の料理か。そのまま料理名（`dish_name`）になる
  2. **写真**: Claude Code が写真を見て、写っている材料・切り方・盛り付けに合う内容にする
  3. **以前の .txt**（あれば）: 以前のツールで作った `recipe.txt` などの材料・分量・作り方にできるだけ合わせる
- 作った内容を、楽天レシピ自動投稿と同じ検証（必須項目・形式）と楽天レシピの文字数チェックにかける。
  問題があれば内容を伝えて作り直してもらう（最大3回）
- 書いた `recipe.yaml` は読み直して、楽天レシピ自動投稿で読み込めることを確かめる

楽天レシピ自動投稿と組み合わせると、次の流れになります。

```
写真を投稿素材のフォルダに置く → このツールで recipe.yaml を作る → 内容を確認（必要なら手で直す） → 楽天レシピ自動投稿で投稿
```

## 必要なもの

- Windows
- [Claude Code](https://claude.com/claude-code)（インストールして、一度 `claude` を起動してログインしておく）
- Python 3.12（exe で使う場合は不要）

Claude Code にログインしているアカウント（Pro / Max などのサブスクリプション）で動くため、APIキーは不要です。
環境変数 `ANTHROPIC_API_KEY` が設定されている場合は、そのAPIキーで従量課金になります。

exe（`Get_RecipeInfo_from_ClaudeCode.exe`）は Git では管理していません。GitHub の Releases からダウンロードするか、[開発](#開発)の手順で作ってください。

## セットアップ

1. `.env.example` を `.env` にコピーして値を設定する（exe で使う場合は exe と同じフォルダに置く）

   | 項目 | 内容 |
   |---|---|
   | `RECIPE_FOLDER` | 投稿素材のフォルダ（楽天レシピ自動投稿の `base_folder_path` と同じ） |
   | `CLAUDE_PATH`（任意） | claude.exe の場所（未指定なら PATH と `%USERPROFILE%\.local\bin\claude.exe` から探す） |
   | `CLAUDE_MODEL`（任意） | 使うモデル（例: `sonnet` / `opus`。未指定なら Claude Code の既定） |
   | `CLAUDE_TIMEOUT`（任意） | 1レシピあたりの待ち時間の上限（秒。未指定なら300） |
   | `LOG_DIR`（任意） | ログの保存先（未指定ならプログラムのフォルダの `logs`） |

   パスは `'` で囲んでください。`"` で囲むと `\t` などが特殊文字として読まれ、フォルダ名が変わってしまうことがあります。

2. Python で動かす場合はパッケージを入れる

   ```bash
   pip install -r requirements.txt
   ```

## 投稿素材の置き方

```
投稿素材\
├── チョレギサラダ\        ← フォルダ名＝料理名（楽天レシピ自動投稿の投稿履歴の recipe_key にもなる）
│   ├── IMG_5740.jpg       ← 料理写真（.jpg / .jpeg / .png）。複数あれば名前順で最初のものをメインにする
│   ├── recipe.txt         ← （任意）以前のレシピの文章。あればこれをもとに作る
│   └── recipe.yaml        ← このツールが作る
└── 豚の角煮\
    └── IMG_5848.jpg
```

`recipe.yaml` の書き方は楽天レシピ自動投稿の [docs/recipe-yaml.md](https://github.com/sbzky1228/sbzky1228-Rakutenreshipi_Automation_Edge/blob/main/docs/recipe-yaml.md) を参照してください。
作られた `recipe.yaml` は手で直してもかまいません（先頭に「Get_RecipeInfo_from_ClaudeCode で作成」というコメントが入ります）。

## 使い方

```bash
python main.py                      # recipe.yaml が無いフォルダすべてに作る
python main.py --folder 豚の角煮     # 指定したフォルダだけ（複数指定可）
python main.py --limit 1            # 1件だけ作る
python main.py --overwrite          # 既にある recipe.yaml も作り直す
python main.py --dry-run            # 作った内容をログに出すだけで、recipe.yaml は書かない（動作確認用）
```

exe の場合も同じ引数が使えます（例: `Get_RecipeInfo_from_ClaudeCode.exe --dry-run`）。
終了コードは、すべて成功（または対象なし）なら 0、作れなかったフォルダがあれば 1 です。

ログは `logs\recipe_generator_日付_時刻.log` に出力されます。

## 注意

- **作った `recipe.yaml` は、楽天レシピ自動投稿を次に実行したときに投稿に使われます**（recipe.txt があっても recipe.yaml が優先）。投稿前に内容、特に「きっかけ」を確認してください
- 楽天レシピに投稿済みのレシピのフォルダで `--overwrite` しても、楽天レシピ側は変わりません（投稿済みのレシピは再投稿されないため）
- Claude Code は実行するたびに文章を作り直すため、同じ写真でも毎回少しずつ違う内容になります
- 1レシピ20〜30秒ほどかかり、Claude のサブスクリプションの利用枠を使います
- 写真が無いフォルダは作りません（楽天レシピは写真が必須のため）

## 開発

```bash
pip install -r requirements-dev.txt
python -X utf8 -m pytest                                              # 自動テスト（Claude Code は呼び出さない）
python -m pyflakes main.py recipe_generator tests                      # 未使用の import・変数など
python -m vulture main.py recipe_generator tests --min-confidence 60   # 使っていないコード
```

GitHub に push すると GitHub Actions（`.github/workflows/tests.yml`）で上記のチェックとテストが自動で実行されます。

exe の作成（`dist` に作られた exe を、`.env` のあるプロジェクト直下へコピーして使う）:

```powershell
python -m PyInstaller --noconfirm --clean --workpath "$env:TEMP\RecipeInfo_build" Get_RecipeInfo_from_ClaudeCode.spec
Copy-Item dist\Get_RecipeInfo_from_ClaudeCode.exe . -Force
```

exe は Git に入れず（`.gitignore` で除外）、配るときは GitHub の Releases に添付します。

### フォルダ構成

```
Get_RecipeInfo_from_ClaudeCode/
├── main.py                    起動するファイル（全体の流れ: 対象フォルダの選択 → 1件ずつ作成・書き出し → 集計）
├── recipe_generator/          プログラム本体
│   ├── config.py              .env の読み込み・設定値
│   ├── logger.py              ログ出力
│   ├── recipes/               レシピフォルダと recipe.yaml
│   │   ├── folders.py         投稿素材フォルダの検出、写真・以前の .txt の検出
│   │   └── model.py           recipe.yaml の読み込み・検証・書き出し（楽天レシピ自動投稿と同じファイル）
│   ├── claude/                Claude Code
│   │   ├── client.py          claude -p の呼び出し（JSONで答えを受け取る）
│   │   ├── prompt.py          プロンプトと答えの形（JSON Schema）
│   │   └── generate.py        答えの検証と作り直し、recipe.yaml の内容づくり
│   └── rakuten/               楽天レシピ
│       └── rules.py           楽天レシピの文字数の上限・絵文字のチェック
├── tests/                     自動テスト
├── Get_RecipeInfo_from_ClaudeCode.spec   exe の作成設定
│
└── （Git に入れないもの）.env、logs/、Get_RecipeInfo_from_ClaudeCode.exe
```

`recipe_generator/recipes/model.py` は楽天レシピ自動投稿の `recipe_poster/recipes/model.py` のコピーで、
`recipe_generator/rakuten/rules.py` の文字数の上限は向こうの `recipe_poster/rakuten/convert.py` と同じ値です。
向こうで変わったらこちらも直してください（隣のフォルダに楽天レシピ自動投稿がある場合は、違っているとテストが失敗して知らせます）。
