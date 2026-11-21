import unicodedata
def cw(c):
    """表示幅（半角=1 / 全角=2）。

    🛑**Ambiguous（'A'）を全角に数えてはいけない。** → — × ± などが該当し、
    pandoc は grid table の枠を数えるときこれらを**半角**として扱う。
    ここで2と数えると枠の位置が pandoc の認識とずれ、**列が黙って結合される**
    （5列の表の1行目だけ崩れ、セル内に '|' が残った）。
    """
    return 2 if unicodedata.east_asian_width(c) in 'WF' else 1
def w(s): return sum(cw(c) for c in s)
# 🛑行頭に置いてはいけない文字（閉じ括弧・句読点・長音など）
NO_HEAD = "）」』】〕〉》、。，．・ー〜！？"
# 🛑行末に置いてはいけない文字（開き括弧）
NO_TAIL = "（「『【〔〈《"
# 元の空白で折り返した行の末尾に付ける目印（私用領域の1文字）。
# 🛑NBSP は使えない: pandoc は grid table のセルを読むとき NBSP も空白として削る
KEEP_SPACE = ""


def _token(s):
    """折り返しの最小単位に分割する。

    🛑**1文字ずつ切ってはいけない。** 半角の英数字・記号（日付やバージョン等）が
    途中で割れて「2024/5-2 / 026/3」のような不自然な改行になる。
    ★半角の連続は1かたまりとして扱い、全角は1文字ずつ扱う。
    """
    out, buf = [], ""
    for ch in s:
        if cw(ch) == 1 and not ch.isspace():
            buf += ch
        else:
            if buf:
                out.append(buf); buf = ""
            out.append(ch)
    if buf:
        out.append(buf)
    return out


def _split_paren(s):
    """「本体」と「（括弧ぶん）」に分ける。括弧が無ければそのまま1つ返す。

    ★括弧の途中で改行されると読みにくい。
    括弧を1つの塊として扱い、可能なら括弧の直前で折り返す。
    """
    i = s.find("（")
    if i <= 0 or not s.rstrip().endswith("）"):
        return [s]
    return [s[:i], s[i:]]


def wrap(s, n):
    """表示幅 n に折り返す（★日本語の禁則処理つき）。

    ★まず「本体」と「（括弧ぶん）」に割り、それぞれが幅に収まるなら
    括弧の直前で改行する。収まらない場合は従来どおり流し込む。
    """
    if w(s) <= n:
        return [s]

    flow = _wrap_flow(s, n)

    # ★括弧が行をまたいで割れているときだけ、括弧の直前で切り直す
    parts = _split_paren(s)
    if len(parts) == 2 and w(parts[1]) <= n:
        head, paren = parts
        cand = _wrap_flow(head.rstrip(), n) + [paren]
        # ★括弧が実際に割れている場合だけ切り直す（割れていないなら触らない）
        paren_split = any(
            ("（" in ln) != ("）" in ln) for ln in flow
        )
        # 🛑最終行の手前が極端に短くなるなら、かえって不自然なので採らない
        #   （例:「社」だけの行ができる）。★1/3 以上埋まっていれば採用
        if paren_split and w(cand[-2]) >= n / 3:
            return cand

    return flow


def _wrap_flow(s, n):
    """幅 n に流し込む（禁則処理つき）。"""
    lines, cur = [], ""
    for tk in _token(s):
        if cur and w(cur) + w(tk) > n:
            # 行頭に来られない文字なら、直前の行に押し込む（ぶら下げ）
            # 🛑ただし枠幅を超えると grid の桁が合わず、pandoc が列を誤認する。
            #   超える場合はぶら下げを諦めて普通に折り返す
            if tk and tk[0] in NO_HEAD and w(cur) + w(tk) <= n:
                cur += tk
                lines.append(cur); cur = ""
                continue
            # 行末に来られない文字は次の行へ送る
            while cur and cur[-1] in NO_TAIL:
                tk = cur[-1] + tk
                cur = cur[:-1]
            # 元の空白の位置で折り返したときは行末に KEEP_SPACE を付ける。
            # cjk_softbreak.lua はこれを見て、その改行だけは空白として残す
            at_space = cur != cur.rstrip() or tk != tk.lstrip()
            lines.append(cur.rstrip() + (KEEP_SPACE if at_space and cur.strip() else ""))
            cur = tk.lstrip()
        else:
            cur += tk
        # 単体でも幅を超えるトークン（長い英数字）は諦めて切る
        while w(cur) > n:
            cut = ""
            for ch in cur:
                if w(cut) + cw(ch) > n:
                    break
                cut += ch
            lines.append(cut); cur = cur[len(cut):]
    if cur:
        lines.append(cur.rstrip())
    return lines or ['']
def grid(rows, cols):
    "rows: list of list[str]; first row is header. cols: display widths (inner, excl 1 pad each side)"
    inner=[c-2 for c in cols]
    def rule(ch): return '+'+'+'.join(ch*c for c in cols)+'+'
    def block(cells):
        ls=[wrap(c,inner[i]) for i,c in enumerate(cells)]
        h=max(len(x) for x in ls)
        out=[]
        for k in range(h):
            parts=[]
            for i,col in enumerate(ls):
                t=col[k] if k<len(col) else ''
                parts.append(' '+t+' '*(cols[i]-1-w(t)))
            out.append('|'+'|'.join(parts)+'|')
        return out
    o=[rule('-')]+block(rows[0])+[rule('=')]
    for r in rows[1:]: o+=block(r)+[rule('-')]
    return '\n'.join(o)+'\n'
