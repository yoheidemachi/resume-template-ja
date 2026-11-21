"""build_docx.py の出力 docx を、PDF（jp_cv.css）の見た目に寄せて Google Docs 向けに整える。
使い方: python3 tools/docx/style_docx_for_gdocs.py in.docx out.docx
"""
import re, sys, zipfile
src, dst = sys.argv[1], sys.argv[2]
FONT = "Noto Sans JP"
RF = f'<w:rFonts w:ascii="{FONT}" w:eastAsia="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>'

def bdr(side, sz, color, space=1):
    return f'<w:{side} w:val="single" w:sz="{sz}" w:space="{space}" w:color="{color}"/>'

H = {  # styleId: (pPr追加, rPr)
 'Heading1': (f'<w:pBdr>{bdr("bottom",16,"333333",3)}</w:pBdr><w:spacing w:before="0" w:after="120"/>',
              f'{RF}<w:b/><w:color w:val="1A1A1A"/><w:spacing w:val="40"/><w:sz w:val="32"/><w:szCs w:val="32"/>'),
 'Heading2': (f'<w:pBdr>{bdr("bottom",8,"555555",2)}</w:pBdr><w:spacing w:before="280" w:after="100"/>',
              f'{RF}<w:b/><w:color w:val="000000"/><w:sz w:val="21"/><w:szCs w:val="21"/>'),
 'Heading3': (f'<w:pBdr>{bdr("left",24,"444444",6)}</w:pBdr><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/><w:spacing w:before="280" w:after="100"/><w:ind w:left="120"/>',
              f'{RF}<w:b/><w:color w:val="1A1A1A"/><w:sz w:val="21"/><w:szCs w:val="21"/>'),
 'Heading4': (f'<w:pBdr>{bdr("bottom",6,"BBBBBB",1)}</w:pBdr><w:spacing w:before="200" w:after="60"/>',
              f'{RF}<w:b/><w:color w:val="444444"/><w:spacing w:val="30"/><w:sz w:val="18"/><w:szCs w:val="18"/>'),
 'Heading5': (f'<w:pBdr>{bdr("left",18,"999999",5)}</w:pBdr><w:spacing w:before="160" w:after="40"/><w:ind w:left="100"/>',
              f'{RF}<w:b/><w:color w:val="1A1A1A"/><w:sz w:val="18"/><w:szCs w:val="18"/>'),
}

def patch_styles(s):
    for sid, (ppr, rpr) in H.items():
        m = re.search(rf'<w:style [^>]*w:styleId="{sid}".*?</w:style>', s, re.S)
        st = m.group(0)
        p = re.search(r'<w:pPr>(.*?)</w:pPr>', st, re.S).group(1)
        p = re.sub(r'<w:spacing [^>]*/>', '', p)
        p = re.sub(r'<w:pBdr>.*?</w:pBdr>|<w:shd [^>]*/>|<w:ind [^>]*/>', '', p, flags=re.S)
        new = re.sub(r'<w:pPr>.*?</w:pPr>', f'<w:pPr>{ppr}{p}</w:pPr>', st, flags=re.S)
        new = re.sub(r'<w:rPr>.*?</w:rPr>', f'<w:rPr>{rpr}</w:rPr>', new, flags=re.S)
        s = s.replace(st, new)
    # 文字の既定フォントを Docs にある Noto Sans JP に固定（游ゴシックは Docs に無く置き換わる）
    s = re.sub(r'(<w:rPrDefault>\s*<w:rPr>)(.*?)(</w:rPr>)',
               lambda m: m.group(1) + RF + re.sub(r'<w:rFonts [^>]*/>', '', m.group(2)) + m.group(3), s, count=1, flags=re.S)
    # 本文 9pt（PDF は 9.2pt。Docs は 0.5pt 刻み）
    s = re.sub(r'(<w:rPrDefault>\s*<w:rPr>.*?)<w:sz w:val="19"\s*/><w:szCs w:val="19"\s*/>', r'\1<w:sz w:val="18"/><w:szCs w:val="18"/>', s, count=1, flags=re.S)
    # 行間: Docs の Noto Sans JP は1行が高く出るので、PDF（3ページ）に寄せて詰める
    s = re.sub(r'(<w:pPrDefault>\s*<w:pPr>\s*)<w:spacing [^>]*/>', r'\1<w:spacing w:before="0" w:after="30" w:line="204" w:lineRule="auto"/>', s, count=1)
    s = re.sub(r'(w:styleId="BodyText".*?)<w:spacing [^>]*/>', r'\1<w:spacing w:before="0" w:after="50" w:line="216" w:lineRule="auto"/>', s, count=1, flags=re.S)
    s = re.sub(r'(w:styleId="Compact".*?)<w:spacing [^>]*/>', r'\1<w:spacing w:before="0" w:after="0" w:line="204" w:lineRule="auto"/>', s, count=1, flags=re.S)
    return s

PAGE_W, MAR_TB, MAR_LR = 11906, 850, 794   # A4・余白 15/14mm（jp_cv.css の @page と同じ）
TEXT_W = PAGE_W - 2 * MAR_LR
FIRST_COL = 1600                           # 2列表の1列目（期間・プロダクト・体制・役割）
CELL_BDR = "".join(bdr(x, 6, "AAAAAA", 0) for x in ("top", "left", "bottom", "right"))
CELL_RPR = f'{RF}<w:sz w:val="17"/><w:szCs w:val="17"/>'

WIDTHS_BY_HEADER = {  # 列幅（%）。PDF の見た目に合わせた比率
    ('期間', '会社・業種', '役割', '主な業務'): [14, 17, 15, 54],
    ('期間', '業種', '役割', '主な業務'): [14, 15, 15, 56],
    ('技術', '期間', 'できること'): [28, 10, 62],
}

def patch_table(t):
    cols = [int(x) for x in re.findall(r'<w:gridCol w:w="(\d+)"', t)]
    first_row = re.search(r'<w:tr\b.*?</w:tr>', t, re.S).group(0)
    heads = tuple(''.join(re.findall(r'<w:t[^>]*>([^<]*)', c)).strip()
                  for c in re.findall(r'<w:tc>.*?</w:tc>', first_row, re.S))
    if heads in WIDTHS_BY_HEADER:   # 中身が空欄（〇〇）でも列幅が偏らないよう、見出しが一致する表は比率で固定する
        pct = WIDTHS_BY_HEADER[heads]
        widths = [round(TEXT_W * x / 100) for x in pct]
    elif len(cols) == 2:
        widths = [FIRST_COL, TEXT_W - FIRST_COL]
    else:
        widths = [round(c * TEXT_W / sum(cols)) for c in cols]
    t = re.sub(r'<w:tblGrid>.*?</w:tblGrid>',
               '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>', t, flags=re.S)
    t = re.sub(r'<w:tblW [^>]*/>', f'<w:tblW w:type="dxa" w:w="{TEXT_W}"/>', t)
    rows = re.findall(r'<w:tr\b.*?</w:tr>', t, re.S)
    for r in rows:
        header = '<w:tblHeader' in r
        cells = re.findall(r'<w:tc>.*?</w:tc>', r, re.S)
        nr = r
        for i, c in enumerate(cells):
            body = re.sub(r'<w:tcPr>.*?</w:tcPr>|<w:tcPr\s*/>', '', c, flags=re.S)
            shd = '<w:shd w:val="clear" w:color="auto" w:fill="F0F0F0"/>' if header else ''
            tcpr = f'<w:tcPr><w:tcW w:w="{widths[min(i, len(widths)-1)]}" w:type="dxa"/><w:tcBorders>{CELL_BDR}</w:tcBorders>{shd}</w:tcPr>'
            body = body.replace('<w:tc>', '<w:tc>' + tcpr, 1)
            # 文字: 8.5pt。表頭は太字（PDF の th と同じ）
            extra = '<w:b/><w:bCs/>' if header else ''
            body = re.sub(r'<w:r>(?!<w:rPr>)', '<w:r><w:rPr></w:rPr>', body)
            body = re.sub(r'<w:rPr>(.*?)</w:rPr>',
                          lambda m: '<w:rPr>' + RF + (extra if '<w:b' not in m.group(1) else '') + re.sub(r'<w:rFonts [^>]*/>|<w:sz [^>]*/>|<w:szCs [^>]*/>', '', m.group(1)) + '<w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr>',
                          body, flags=re.S)
            nr = nr.replace(c, body, 1)
        t = t.replace(r, nr, 1)
    return t

def patch_doc(d):
    d = re.sub(r'<w:tbl>.*?</w:tbl>', lambda m: patch_table(m.group(0)), d, flags=re.S)
    # タイトルは PDF と同じ左寄せ（build_docx.py は中央にしている）。pStyle を先頭に戻す
    d = d.replace('<w:pPr><w:jc w:val="center"/><w:pStyle w:val="Heading1" /></w:pPr>', '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>')
    # pPr の中は pStyle が先頭（スキーマ順）。build_docx.py は jc を先に入れている
    d = re.sub(r'<w:pPr>(<w:jc [^>]*/>)(<w:pStyle [^>]*/>)', r'<w:pPr>\2\1', d)
    d = re.sub(r'<w:pgMar [^>]*/>', f'<w:pgMar w:top="{MAR_TB}" w:right="{MAR_LR}" w:bottom="{MAR_TB}" w:left="{MAR_LR}" w:header="500" w:footer="500" w:gutter="0"/>', d)
    # Markdown の --- 由来の水平線を消す（PDF では非表示）
    d = re.sub(r'<w:p><w:r><w:pict><v:rect [^>]*o:hr="t"\s*/></w:pict></w:r></w:p>', '', d)
    # 斜体（em）は PDF では「斜体にしないグレー」
    d = re.sub(r'<w:i\s*/>', '<w:color w:val="555555"/>', d)
    d = re.sub(r'<w:iCs\s*/>', '', d)
    return d

zin = zipfile.ZipFile(src)
zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for it in zin.infolist():
    data = zin.read(it.filename)
    if it.filename == 'word/styles.xml':
        data = patch_styles(data.decode('utf-8')).encode('utf-8')
    elif it.filename == 'word/numbering.xml':
        data = re.sub(r'(<w:lvl w:ilvl="0">.*?)<w:ind w:left="720" w:hanging="360"\s*/>', r'\1<w:ind w:left="300" w:hanging="220"/>', data.decode('utf-8'), flags=re.S).encode('utf-8')
    elif it.filename == 'word/document.xml':
        data = patch_doc(data.decode('utf-8')).encode('utf-8')
    zout.writestr(it, data)
zout.close()
print('wrote', dst)
