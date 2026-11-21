#!/usr/bin/env python3
"""Markdown の職務経歴書 → Word(.docx) を生成する。

pandoc の既定 reference.docx は pgSz/pgMar を持たないため Word が US レター
＋1インチ余白で開き、ページ数が膨らむ。また pipe table は列幅が均等割りに
なり、日本語だと各セルが何度も折り返して読めなくなる。

対処:
  1. reference_jp.docx  … A4・余白・游ゴシック（Windows 標準＝先方環境で置換されない）
  2. pipe table → grid table  … pandoc は grid table の枠幅を列幅として尊重する
     ★日本語は全角なので、枠を描くときに East Asian Width で数える（gridgen）

使い方:
    python3 tools/docx/build_docx.py <入力.md> <出力.docx>
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gridgen import cw, grid, w  # noqa: E402

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "reference_jp.docx"

# 本文の表示幅（半角換算）。A4・余白15/16mm・9.5pt でおよそこの程度が収まる上限。
TOTAL_WIDTH = 104


def split_row(line):
    """| a | b | → ['a','b']"""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(line):
    return bool(re.fullmatch(r"\|[\s:\-|]+\|", line.strip()))


def column_widths(rows, total):
    """各列の内容長に比例して幅を配分する。

    🛑**列が結合される事故を防ぐのがこの関数の役目。** pandoc の grid table は
    セルの中身が枠に収まらないと列を黙って結合する（5列→2列→1列に潰れる）。
    セルは wrap() で折り返されるので幅が足りなくても字は消えないが、
    ★極端に狭い列を作ると1文字ずつ折り返して読めなくなるため、最低幅を確保する。
    """
    ncol = len(rows[0])
    avail = total - ncol - 1  # 枠線 '|' の分を引いた、文字を置ける合計幅
    MIN = 10                  # 1列あたりの最低表示幅（これを割ると縦書き状態になる）

    # 🛑「割ってはいけない塊」（日付・英数字など半角の連続）が入る列は、
    #   その最長トークンぶんの幅を必ず確保する。確保しないと 2024/5-2026/3 が
    #   「2024/5-2 / 026/3」のように途中で割れる
    import re as _re
    need = []
    for i in range(ncol):
        longest = 0
        for r in rows:
            cell = r[i].strip()
            # ★セル全体が半角の塊（日付レンジ等）なら、その全長を確保する
            if cell and all(cw(c) == 1 for c in cell):
                longest = max(longest, len(cell))
            else:
                for tk in _re.findall(r"[0-9A-Za-z/().,:+-]+", cell):
                    longest = max(longest, len(tk))
        # 🛑 grid() はセルの左右に1桁ずつパディングを入れるので +2 が要る
        need.append(min(longest + 2, avail // 3))

    if avail < MIN * ncol:    # そもそも入らない列数なら均等割り
        base = max(4, avail // ncol)
        cols = [base] * ncol
    else:
        # 各列の最大セル幅に比例配分する（見出しも含める）
        raw = [max(w(r[i]) for r in rows) for i in range(ncol)]
        scale = avail / max(sum(raw), 1)
        cols = [max(MIN, need[i], int(r * scale)) for i, r in enumerate(raw)]
        # 最低幅の底上げで溢れた分を、広い列から順に削る
        over = sum(cols) - avail
        while over > 0:
            # ★削ってよいのは「最低幅」と「割れない塊の幅」を上回っている列だけ
            cand = [i for i in range(ncol) if cols[i] > max(MIN, need[i])]
            if not cand:
                break
            i = max(cand, key=lambda k: cols[k])
            cols[i] -= 1
            over -= 1

    diff = avail - sum(cols)  # 端数は最も広い列で吸収
    cols[cols.index(max(cols))] += diff
    return cols


def hard_breaks(md):
    """連続する行に強制改行を入れる。

    🛑**Markdown の単なる改行は pandoc に無視され、段落内で1行に連結される。**
    PDF 経路（md2html.py）は独自に <br> を出していたので問題にならなかったが、
    pandoc ではラベル行（**期間:** …／**役割:** …）が
    すべて1段落に繋がって読めなくなる。
    → ★行末に半角スペース2つを付けて hard line break にする。

    ★表・箇条書き・見出し・空行の前後には付けない（構造が壊れるため）。
    """
    # 🛑「**太字」を箇条書き（*）と誤判定しないこと。リスト記号はスペースを伴う。
    LIST = re.compile(r"^([-+*]\s|\d+[.)]\s|>|#|\||\+-)")

    def structural(s):
        return not s.strip() or bool(LIST.match(s.strip()))

    out = []
    lines = md.split("\n")
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        keep = structural(line) or structural(nxt) or line.endswith("  ")
        out.append(line if keep else line + "  ")
        # 🛑リストの直前に空行が無いと pandoc はリストと認識せず、
        #   地の文に "- " が残り、箇条書きが1段落に潰れる
        # 🛑🛑ただし grid table の中（|…| や +--+ の行）には入れてはいけない。
        #   表が行ごとにバラバラの段落へ分解され、罫線がそのまま本文に出る（実測）。
        in_table = line.lstrip().startswith(("|", "+")) or nxt.lstrip().startswith(("|", "+"))
        if line.strip() and not in_table and LIST.match(nxt.strip() or "\0"):
            out.append("")
    return "\n".join(out)


def convert_tables(md):
    """pipe table を grid table へ置き換える。"""
    out, buf = [], []

    def flush():
        if not buf:
            return
        rows = [split_row(l) for l in buf if not is_separator(l)]
        if len(rows) >= 2 and len({len(r) for r in rows}) == 1:
            out.append(grid(rows, column_widths(rows, TOTAL_WIDTH)))
        else:  # 表として解釈できなければ原文のまま
            out.extend(l + "\n" for l in buf)
        buf.clear()

    for line in md.splitlines(keepends=True):
        if line.lstrip().startswith("|"):
            buf.append(line.rstrip("\n"))
        else:
            flush()
            out.append(line)
    flush()
    return "".join(out)


# 表の体裁
HEADER_FILL = "E7E6E6"   # ヘッダー行の背景（薄いグレー）
BORDER_SZ = "8"          # 罫線の太さ（1/8pt 単位）


def style_tables(doc):
    """表に罫線とヘッダー背景を入れる。

    ★pandoc の既定はヘッダー下の横罫線だけで、枠線も背景も無い。
    全セルに細い罫線＋ヘッダー行に薄いグレーを敷く。
    """
    sides = "".join(
        f'<w:{s} w:val="single" w:sz="{BORDER_SZ}" w:space="0" w:color="auto"/>'
        for s in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    borders = f"<w:tblBorders>{sides}</w:tblBorders>"

    def add_borders(m):
        pr = m.group(0)
        return pr if "<w:tblBorders>" in pr else pr.replace(
            "</w:tblPr>", f"{borders}</w:tblPr>", 1)

    doc = re.sub(r"<w:tblPr>.*?</w:tblPr>", add_borders, doc, flags=re.S)

    # ヘッダー行（tblHeader 指定のある行）のセルに背景を敷く
    # 🛑<w:tcPr> が無いセルもあるので、その場合は <w:tc> の直後に作る
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{HEADER_FILL}"/>'

    def shade_cell(m):
        cell = m.group(0)
        if "<w:shd" in cell:
            return cell
        if "<w:tcPr>" in cell:
            return cell.replace("<w:tcPr>", f"<w:tcPr>{shd}", 1)
        return cell.replace("<w:tc>", f"<w:tc><w:tcPr>{shd}</w:tcPr>", 1)

    def shade_header(m):
        row = m.group(0)
        if "<w:tblHeader" not in row:
            return row
        return re.sub(r"<w:tc\b.*?</w:tc>", shade_cell, row, flags=re.S)

    return re.sub(r"<w:tr\b.*?</w:tr>", shade_header, doc, flags=re.S)


def page_break_before_history(doc):
    """「職務経歴（時系列）」の見出しの前で改ページする。

    ★この節は表2つ＋補足で1ページに収まるので、途中でページをまたぐと読みにくい
    → 見出しの前で送って、節ごと1ページに載せる。

    🛑**実績詳細の各案件には入れない。** 案件ごとに改ページすると短い案件（半ページ程度）で
    白紙が大きく空く。
    """
    edits = []
    for m in re.finditer(r"<w:p\b.*?</w:p>", doc, re.S):
        body = m.group(0)
        text = re.sub(r"<[^>]+>", "", body)
        style = re.search(r'<w:pStyle w:val="([^"]+)"\s*/>', body)
        style = style.group(1) if style else ""

        if not style.startswith("Heading") or "職務経歴" not in text or "時系列" not in text:
            continue
        if "<w:pageBreakBefore" in body:
            continue
        if "<w:pPr>" in body:
            new_body = body.replace("<w:pPr>", "<w:pPr><w:pageBreakBefore/>", 1)
        else:
            new_body = body.replace("<w:p>", "<w:p><w:pPr><w:pageBreakBefore/></w:pPr>", 1)
        edits.append((m.start(), m.end(), new_body))

    for start, end, new_body in reversed(edits):
        doc = doc[:start] + new_body + doc[end:]

    # 🛑直前の区切り線（Markdown の `---`）を消す。改ページで節は区切れるので不要なうえ、
    #   前のページが埋まっていると線だけが次ページに送られ、白紙が1枚挟まる
    doc = re.sub(
        r'<w:p><w:r><w:pict><v:rect [^>]*o:hr="t"\s*/></w:pict></w:r></w:p>\s*'
        r'((?:<w:bookmark(?:End|Start)\b[^>]*/>\s*)*)'
        r'(?=<w:p><w:pPr><w:pageBreakBefore/>)',
        r"\1",
        doc,
    )
    return doc


def align_header(docx_path):
    """タイトルを中央揃え、直後の日付・氏名を右揃えにする。

    ★日本の職務経歴書の作法。
    pandoc は Markdown から配置を出せないので、生成後の docx を直接直す。
    """
    import shutil
    import zipfile

    with zipfile.ZipFile(docx_path) as z:
        items = {n: z.read(n) for n in z.namelist()}

    doc = items["word/document.xml"].decode("utf-8")

    # 🛑段落の「番号」で位置を決めない。日付と氏名が1段落にまとまるかは
    #   pandoc の改行処理次第で変わり、ずれると見出しまで右寄せになる（実測）。
    #   → ★見出しスタイル（Title/Heading1）と、それに続く本文段落で判定する。
    edits = []
    seen_title = False
    for m in re.finditer(r"<w:p\b.*?</w:p>", doc, re.S):
        body = m.group(0)
        # 🛑pandoc は `<w:pStyle w:val="X" />` とスラッシュ前にスペースを入れる。
        #   `"/>` 決め打ちだと一致せず、配置が一切入らない
        style = re.search(r'<w:pStyle w:val="([^"]+)"\s*/>', body)
        style = style.group(1) if style else ""

        if style in ("Title", "Heading1") and not seen_title:
            seen_title, align = True, "center"
        elif seen_title and not style.startswith("Heading"):  # タイトル直後の本文＝日付・氏名
            align = "right"
        else:                                   # 次の見出しが来たら打ち切る
            break

        if "<w:pPr>" in body:
            new_body = body.replace("<w:pPr>", f'<w:pPr><w:jc w:val="{align}"/>', 1)
        else:
            new_body = body.replace("<w:p>", f'<w:p><w:pPr><w:jc w:val="{align}"/></w:pPr>', 1)
        edits.append((m.start(), m.end(), new_body))

    for start, end, new_body in reversed(edits):
        doc = doc[:start] + new_body + doc[end:]
    doc = style_tables(doc)
    doc = page_break_before_history(doc)
    items["word/document.xml"] = doc.encode("utf-8")

    tmp = str(docx_path) + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items.items():
            z.writestr(name, data)
    shutil.move(tmp, docx_path)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    md = hard_breaks(convert_tables(src.read_text(encoding="utf-8")))

    # ★経歴書の中身を一時ファイルに書き出さない（氏名・勤務先の写しを残さないため）。
    #   pandoc には標準入力で渡す。
    # 🛑east_asian_line_breaks を付けないと、grid table のセル内の折り返し位置に
    #   pandoc が半角スペースを入れ、「本番ロー ンチ」「アクセ ス」のように語が割れる
    subprocess.run(
        ["pandoc", "-f", "markdown+east_asian_line_breaks", "-t", "docx",
         f"--lua-filter={Path(__file__).with_name('cjk_softbreak.lua')}",
         f"--reference-doc={REFERENCE}", "-o", str(dst)],
        input=md, text=True, encoding="utf-8",
        check=True,
    )
    align_header(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
