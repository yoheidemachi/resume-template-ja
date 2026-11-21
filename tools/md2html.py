#!/usr/bin/env python3
"""Minimal Markdown -> HTML for resume/rirekisho PDF generation.
Supports: h1-h3, hr, tables, bullet lists, bold, italic, inline code, links, paragraphs.
"""
import sys, re, html


def inline(t):
    # escape first, then re-introduce markup
    t = html.escape(t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\w)\*([^*]+?)\*(?!\w)', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+?)`', r'<code>\1</code>', t)
    return t


def convert(md):
    lines = md.split('\n')
    out = []
    i = 0
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append('</ul>')
            in_list = False

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            close_list()
            i += 1
            continue

        # table
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:\-|]+\|$', lines[i + 1].strip()):
            close_list()
            hdr = [c.strip() for c in s.strip('|').split('|')]
            # year/month tables: pin narrow columns with explicit width attrs,
            # since LibreOffice's HTML importer ignores much of the CSS.
            ymd = hdr[:2] == ['年', '月']

            def cell(tag, text, idx):
                attr = ''
                if ymd and idx == 0:
                    attr = ' width="46" nowrap="nowrap"'
                elif ymd and idx == 1:
                    attr = ' width="34" nowrap="nowrap"'
                return f'<{tag}{attr}>{inline(text)}</{tag}>'

            out.append('<table><thead><tr>'
                       + ''.join(cell('th', c, n) for n, c in enumerate(hdr))
                       + '</tr></thead><tbody>')
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                out.append('<tr>' + ''.join(cell('td', c, n) for n, c in enumerate(cells)) + '</tr>')
                i += 1
            out.append('</tbody></table>')
            continue

        if s.startswith('---'):
            close_list()
            out.append('<hr>')
            i += 1
            continue

        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            close_list()
            lvl = len(m.group(1))
            out.append(f'<h{lvl}>{inline(m.group(2))}</h{lvl}>')
            i += 1
            continue

        m = re.match(r'^[-*]\s+(.*)$', s)
        if m:
            if not in_list:
                out.append('<ul>')
                in_list = True
            # LibreOffice ignores align on <li>; wrap the content in an aligned <p>
            out.append(f'<li><p align="left">{inline(m.group(1))}</p></li>')
            i += 1
            continue

        close_list()
        # inline align attr: LibreOffice's importer justifies <p> otherwise
        align = 'right' if (out and out[-1].startswith('<h1>')) else 'left'
        # tag the date/subtitle line under a heading so CSS can style just it
        cls = ' class="sub"' if (out and re.match(r'^<h[13]>', out[-1])) else ''
        out.append(f'<p align="{align}"{cls}>{inline(s)}</p>')
        i += 1

    close_list()
    return '\n'.join(out)


if __name__ == '__main__':
    md_path, css_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(md_path, encoding='utf-8') as f:
        body = convert(f.read())
    with open(css_path, encoding='utf-8') as f:
        css = f.read()
    doc = (f'<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
           f'<style>{css}</style></head><body>{body}</body></html>')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'wrote {out_path}')
