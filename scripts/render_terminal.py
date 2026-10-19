"""Render captured command output (*.txt) as terminal-style PNGs for the report.

Usage: python scripts/render_terminal.py <evidence_dir> <output_dir>
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TEMPLATE = """<html><head><style>
body {{ margin:0; background:#eef1f5; font-family: -apple-system, Segoe UI, sans-serif; }}
.win {{ margin:24px; border-radius:10px; overflow:hidden; box-shadow:0 6px 24px rgba(0,0,0,.25);
        width: fit-content; min-width: 900px; max-width: 1400px; }}
.bar {{ background:#2d2f36; color:#c9ced6; padding:9px 14px; font-size:13px; }}
.dot {{ display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:6px; }}
pre {{ margin:0; background:#16181d; color:#e6e6e6; padding:16px 18px; font-size:13px;
       line-height:1.45; font-family: Menlo, Consolas, monospace; white-space: pre-wrap; }}
.cmd {{ color:#7ee787; }}
</style></head><body><div class="win" id="w">
<div class="bar"><span class="dot" style="background:#ff5f57"></span>
<span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840">
</span>&nbsp; {title}</div><pre>{body}</pre></div></body></html>"""


def to_html(path: Path) -> str:
    lines = []
    for line in path.read_text(errors="replace").splitlines()[-120:]:
        esc = html.escape(line)
        lines.append(f'<span class="cmd">{esc}</span>' if line.startswith("$ ") else esc)
    title = path.stem.replace("_", " ")
    return TEMPLATE.format(title=html.escape(title), body="\n".join(lines))


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 900})
        for txt in sorted(src.glob("*.txt")):
            page.set_content(to_html(txt))
            page.locator("#w").screenshot(path=out / f"{txt.stem}.png")
            print(f"rendered {txt.stem}.png")
        browser.close()


if __name__ == "__main__":
    main()
