# エンジニア向け 職務経歴書ひな形（Markdown 版）

エンジニアの転職で出す **職務経歴書を Markdown で書き、PDF や Google ドキュメントに仕上げる** ためのひな形とツールです。

Markdown で書くと、AI に下書きや言い回しの手直しを頼みやすく、差分も追いやすくなります。
書き終えたら、このリポジトリのツールで見た目を整えて提出用のファイルにします。

- そのまま提出するなら **PDF**
- 転職エージェントや知人に直してもらうなら **Google ドキュメント**（コメントや提案モードが使えます）

## 入っているもの

| ファイル | 中身 |
|:---|:---|
| `職務経歴書_ひな形.md` | 空欄（〇〇）のひな形。これを写して自分の経歴を書く |
| `tools/md2html.py` | Markdown を HTML にする（Python の標準ライブラリだけで動く） |
| `tools/jp_cv.css` | PDF の見た目（A4・見出し・表・ページ番号） |
| `tools/docx/build_docx.py` | Markdown を Word（.docx）にする。表の列幅と日本語の折り返しを調整する |
| `tools/docx/gridgen.py`・`cjk_softbreak.lua`・`reference_jp.docx` | `build_docx.py` が使う部品 |
| `tools/docx/style_docx_for_gdocs.py` | .docx を Google ドキュメント向けに整える（見出しの線・表の色・フォント） |
| `AGENTS.md`（`CLAUDE.md` はその別名） | AI のコーディングエージェントに読ませる作業メモ |

## ⚠️ 自分の経歴書を公開リポジトリに push しない

経歴書には氏名や勤務先が入ります。このリポジトリを fork してそのまま書き込むと、**誰でも読める場所に経歴書が載ります**。

- 手元に clone して、ひな形を写したファイルは push しない
- 履歴を管理したいなら、**private リポジトリ**を別に作ってそこへ置く

`.gitignore` で `my/` フォルダと `out/` フォルダを除外してあるので、自分の経歴書は `my/` に置くのがおすすめです。

## 準備

Python 3 が入っていれば、あとは次の2つを入れます。

| 道具 | 使う場面 | macOS（Homebrew） | その他 |
|:---|:---|:---|:---|
| [WeasyPrint](https://weasyprint.org/) | PDF を作る | `brew install weasyprint` | Ubuntu・Debian は `sudo apt install weasyprint`。ほかは[公式の手順](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) |
| [pandoc](https://pandoc.org/) | Word・Google ドキュメントを作る | `brew install pandoc` | [公式のインストール手順](https://pandoc.org/installing.html) |

Windows では WeasyPrint の準備に手間がかかります。WSL の Ubuntu を使えるなら、`sudo apt install weasyprint pandoc fonts-noto-cjk` で3つとも入ります。WSL を使わない方法は公式の手順にあります。
Linux でも日本語フォント（`fonts-noto-cjk` など）が要ります。

入ったかどうかの確認:

```bash
weasyprint --version
pandoc --version
```

## 使い方

### 1. ひな形を写して書く

```bash
git clone https://github.com/yoheidemachi/resume-template-ja.git
cd resume-template-ja
mkdir -p my out
cp 職務経歴書_ひな形.md my/職務経歴書.md
```

`my/職務経歴書.md` の「〇〇」を埋めていきます。AI に頼むときは、ひな形の見出しと表の形を崩さないように伝えると、そのまま変換できます。

書くときの注意:

- 見出しの段（`#`・`##`・`###`・`####`）はひな形のまま使う。見た目は段ごとに決まっている
- 段落の途中で改行しない。1つの段落は1行で書く
- 表は `| 期間 | ... |` の形のまま。列を増やしても動くが、多すぎると狭くなる

### 2. PDF にする

```bash
python3 tools/md2html.py my/職務経歴書.md tools/jp_cv.css out/職務経歴書.html
weasyprint out/職務経歴書.html out/職務経歴書.pdf
```

`out/職務経歴書.pdf` ができます。ブラウザで `out/職務経歴書.html` を開くと、PDF にする前の見た目を確かめられます。

`Fontconfig error: No writable cache directories` と出ても、PDF ができていれば問題ありません。

### 3. Google ドキュメントにする

```bash
python3 tools/docx/build_docx.py my/職務経歴書.md out/base.docx
python3 tools/docx/style_docx_for_gdocs.py out/base.docx out/職務経歴書.docx
```

1. パソコンで [Google ドライブの設定](https://drive.google.com/drive/settings)を開き、「アップロードしたファイルを Google ドキュメント エディタ形式に変換する」にチェックを入れる
2. [Google ドライブ](https://drive.google.com/)に `out/職務経歴書.docx` をアップロードする。自動で Google ドキュメントに変換される
3. ページ番号が要るなら「挿入」→「ページ番号」で足す

1の設定をしないでアップロードした場合は、Word ファイルのまま開きます。ファイルをダブルクリックして開き、「ファイル」メニューから Google ドキュメント形式で保存してください。
詳しくは Google のヘルプ「[Office ファイルの使用](https://support.google.com/docs/answer/6055139?hl=ja)」にあります。

Google ドキュメントではフォントが Noto Sans JP になります。見出しの線・表の色・A4 の余白は PDF とほぼ同じに出ます。

Word で出したい場合は、1行目の `out/base.docx` をそのまま使えます。

## 困ったとき

| 症状 | 原因と対処 |
|:---|:---|
| `weasyprint: command not found` | WeasyPrint が入っていない。「準備」を参照 |
| `pandoc` が見つからないと出る | pandoc が入っていない。「準備」を参照 |
| PDF の日本語が豆腐（□）になる | 日本語フォントが無い。Linux・WSL なら `fonts-noto-cjk` を入れる |
| 表の列がつぶれて1列になる（docx） | 表の行ごとに列の数がそろっているか確かめる |
| 箇条書きが本文に `- ` のまま出る | 箇条書きの前に空行を入れる |

## ライセンス

[MIT](LICENSE)
