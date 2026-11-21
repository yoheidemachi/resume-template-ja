# AGENTS.md

> このファイルが AI エージェント向けガイドの正本です。`CLAUDE.md` はこのファイルへの symlink です。
> 編集はこの `AGENTS.md` に対して行ってください。

## このリポジトリ

エンジニア向けの職務経歴書を Markdown で書き、PDF・Word・Google ドキュメントに変換するためのひな形とツール。
使い方は `README.md` を読むこと。

## 経歴書を書く・直すとき

- 書き込むのは `my/` の下のファイル。`職務経歴書_ひな形.md` は空欄のまま残す
- `my/` と `out/` は `.gitignore` 済み。**利用者の経歴書を commit・push しない**（氏名・勤務先が入るため）
- 利用者が言っていない経歴・数字・資格を作らない。足りない情報は質問する
- 見出しの段（`#` 〜 `#####`）と表の形はひな形に合わせる。見た目は段ごとに `tools/jp_cv.css` で決まっている
- 1つの段落は1行で書く（途中で改行しない）

## 変換

```bash
# PDF
python3 tools/md2html.py my/職務経歴書.md tools/jp_cv.css out/職務経歴書.html
weasyprint out/職務経歴書.html out/職務経歴書.pdf

# Google ドキュメント用の docx
python3 tools/docx/build_docx.py my/職務経歴書.md out/base.docx
python3 tools/docx/style_docx_for_gdocs.py out/base.docx out/職務経歴書.docx
```

変換したら PDF を画像にして（`pdftoppm -png` など）、表が崩れていないか目で確かめる。
