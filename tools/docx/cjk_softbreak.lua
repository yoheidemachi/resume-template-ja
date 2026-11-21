-- 和文と欧文の境目の改行で入る半角スペースを消す。
-- east_asian_line_breaks は「両側が和文」のときしか改行を消さないため、
-- grid table の折り返しが「91%｜減」「・｜SLI/SLO」で切れると
-- 「91% 減」「監視・ SLI/SLO」のように余計な空白が入る。
-- 改行（SoftBreak）の前後どちらかが和文なら、空白を入れずにつなぐ。

local function is_wide(cp)
  return (cp >= 0x3000 and cp <= 0x9FFF)
      or (cp >= 0xF900 and cp <= 0xFAFF)
      or (cp >= 0xFF00 and cp <= 0xFFEF)
end

local function last_cp(s)
  return utf8.codepoint(s, utf8.offset(s, -1))
end

local function first_cp(s)
  return utf8.codepoint(s, 1)
end

-- gridgen.py が「元の空白で折り返した行」の末尾に付ける目印（私用領域 U+E000）
local KEEP_SPACE = "\u{E000}"

function Inlines(inlines)
  local out = pandoc.Inlines {}
  for i, el in ipairs(inlines) do
    local prev = inlines[i - 1]
    if el.t == "SoftBreak" and prev and prev.t == "Str"
        and prev.text:sub(-#KEEP_SPACE) == KEEP_SPACE then
      -- 元に空白があった改行: 目印を外し、空白として残す
      out[#out] = pandoc.Str(prev.text:sub(1, -#KEEP_SPACE - 1))
      out:insert(pandoc.Space())
    elseif el.t == "SoftBreak" then
      local next = inlines[i + 1]
      local prev_wide = prev and prev.t == "Str" and is_wide(last_cp(prev.text))
      local next_wide = next and next.t == "Str" and is_wide(first_cp(next.text))
      if not (prev_wide or next_wide) then
        out:insert(el)
      end
    else
      out:insert(el)
    end
  end
  return out
end
