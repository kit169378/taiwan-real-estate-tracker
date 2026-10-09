"""把 Markdown 報告轉成 email 用的 HTML（支援表格，樣式寫成 inline 以相容 Gmail）。

用法：python scripts/md_to_email.py <input.md> <output.html>
"""
import sys

import markdown

STYLES = {
    "<table>": '<table style="border-collapse:collapse;margin:12px 0;font-size:14px;">',
    "<th>": '<th style="border:1px solid #ccc;padding:6px 10px;background:#f2f2f2;text-align:left;">',
    "<td>": '<td style="border:1px solid #ccc;padding:6px 10px;vertical-align:top;">',
}

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    html = markdown.markdown(f.read(), extensions=["tables", "sane_lists"])

# tables 擴充會為對齊欄位輸出 <th style="text-align:...">，先補上框線，再處理一般標籤
html = html.replace('<th style="', '<th style="border:1px solid #ccc;padding:6px 10px;background:#f2f2f2;')
html = html.replace('<td style="', '<td style="border:1px solid #ccc;padding:6px 10px;vertical-align:top;')
for tag, styled in STYLES.items():
    html = html.replace(tag, styled)

with open(dst, "w", encoding="utf-8") as f:
    f.write(
        '<html><head><meta charset="utf-8"></head>'
        '<body style="font-family:Arial,\'Microsoft JhengHei\',sans-serif;line-height:1.6;color:#222;">'
        f"{html}</body></html>"
    )
