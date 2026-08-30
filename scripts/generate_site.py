#!/usr/bin/env python3
"""data/articles.json 을 읽어서 docs/index.html 매거진 페이지를 생성한다."""
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "articles.json"
OUT_FILE = ROOT / "docs" / "index.html"
FONT_SRC_DIR = ROOT / "assets" / "fonts"
FONT_OUT_DIR = ROOT / "docs" / "assets" / "fonts"

FEATURED_TEMPLATE = """
<a class="featured" href="{link}" target="_blank" rel="noopener">
  {image_html}
  <div class="featured-text">
    <div class="featured-tag">Featured</div>
    <h2 class="featured-title">{title}</h2>
    <p class="featured-summary">{summary}</p>
    <div class="item-meta">{source} · {published}{tags_suffix}</div>
  </div>
</a>
"""

ITEM_TEMPLATE = """
<a class="item" href="{link}" target="_blank" rel="noopener">
  <div class="item-text">
    <h2 class="item-title">{title}</h2>
    <p class="item-summary">{summary}</p>
    <div class="item-meta">{source} · {published}{tags_suffix}</div>
  </div>
  {image_html}
</a>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Silver Information</title>
<style>
  @font-face {{
    font-family: "Noto Serif KR";
    font-weight: 500;
    src: url("assets/fonts/NotoSerifKR-Medium.woff2") format("woff2");
    font-display: swap;
  }}
  @font-face {{
    font-family: "Noto Serif KR";
    font-weight: 700;
    src: url("assets/fonts/NotoSerifKR-Bold.woff2") format("woff2");
    font-display: swap;
  }}
  :root {{
    --bg: #0a0a0a;
    --bg-soft: #111111;
    --ink: #f2f2f0;
    --muted: #8a8a85;
    --line: #232323;
    --silver-1: #ffffff;
    --silver-2: #b8b8b8;
    --silver-3: #6e6e6e;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background:
      radial-gradient(ellipse 900px 500px at 50% -10%, #1c1c1c 0%, var(--bg) 60%);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Apple SD Gothic Neo", sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  header {{
    max-width: 760px;
    margin: 0 auto;
    padding: 56px 20px 8px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  header h1 {{
    font-family: Helvetica, Arial, sans-serif;
    font-weight: 700;
    font-size: 34px;
    letter-spacing: -0.01em;
    margin: 0;
    color: var(--ink);
  }}
  header .menu {{
    display: flex;
    padding-top: 12px;
  }}
  header .menu a {{
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
    text-decoration: none;
    margin-left: 18px;
  }}
  header .menu a:hover {{ color: var(--ink); }}
  .rule {{
    max-width: 760px;
    margin: 28px auto 0;
    padding: 0 20px;
  }}
  .rule::after {{
    content: "";
    display: block;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--silver-3) 20%, var(--silver-2) 50%, var(--silver-3) 80%, transparent);
    opacity: 0.5;
  }}
  main {{
    max-width: 760px;
    margin: 0 auto;
    padding: 8px 20px 80px;
  }}
  .featured {{
    display: block;
    text-decoration: none;
    color: inherit;
    padding: 36px 0 32px;
    border-bottom: 1px solid var(--line);
  }}
  .featured-thumb {{
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    display: block;
    background: var(--bg-soft);
    margin-bottom: 22px;
  }}
  .featured-tag {{
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--silver-2);
    margin-bottom: 10px;
  }}
  .featured-title {{
    font-family: "Noto Serif KR", serif;
    font-weight: 700;
    font-size: 26px;
    line-height: 1.35;
    margin: 0 0 12px;
    color: var(--ink);
  }}
  .featured-summary {{
    font-size: 14px;
    color: #b0b0ab;
    line-height: 1.7;
    margin: 0 0 14px;
  }}
  .item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    padding: 24px 0;
    border-bottom: 1px solid var(--line);
    text-decoration: none;
    color: inherit;
  }}
  main .item:last-child {{ border-bottom: none; }}
  .item-text {{
    flex: 1;
    min-width: 0;
  }}
  .item-title {{
    font-family: "Noto Serif KR", serif;
    font-weight: 500;
    font-size: 18px;
    letter-spacing: 0;
    margin: 0 0 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--ink);
  }}
  .item-summary {{
    font-size: 13px;
    color: #a8a8a3;
    line-height: 1.5;
    margin: 0 0 10px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .item-meta {{
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .item-thumb {{
    width: 96px;
    height: 96px;
    flex-shrink: 0;
    object-fit: cover;
    background: var(--bg-soft);
  }}
  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 0.06em;
    padding: 0 0 56px;
  }}
</style>
</head>
<body>
<header>
  <h1>Silver Information</h1>
  <nav class="menu">
    <a href="instagram/index.html">Instagram</a>
    <a href="drafts/index.html">Drafts</a>
  </nav>
</header>
<div class="rule"></div>
<main>
{items}
</main>
<footer>brands.txt 태그로 자동 필터링된 개인 매거진</footer>
</body>
</html>
"""


def esc(s):
    return html.escape(s or "", quote=False)


def main():
    if not DATA_FILE.exists():
        articles = []
    else:
        articles = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    items = []
    for idx, a in enumerate(articles):
        tags_suffix = ""
        if a.get("matched_brands"):
            tags_suffix = " · " + esc(" / ".join(a["matched_brands"]))

        common = dict(
            source=esc(a.get("source", "")),
            published=esc(a.get("published", ""))[:16],
            link=a.get("link", "#"),
            title=esc(a.get("title", "")),
            summary=esc(a.get("summary", "")),
            tags_suffix=tags_suffix,
        )

        if idx == 0:
            image_html = ""
            if a.get("image"):
                image_html = (
                    f'<img class="featured-thumb" src="{esc(a["image"])}" alt="" loading="lazy" '
                    f'onerror="this.style.display=\'none\'">'
                )
            items.append(FEATURED_TEMPLATE.format(image_html=image_html, **common))
        else:
            image_html = ""
            if a.get("image"):
                image_html = (
                    f'<img class="item-thumb" src="{esc(a["image"])}" alt="" loading="lazy" '
                    f'onerror="this.style.display=\'none\'">'
                )
            items.append(ITEM_TEMPLATE.format(image_html=image_html, **common))

    page = PAGE_TEMPLATE.format(
        items="\n".join(items) if items else "<p style='color:#8a8a85'>아직 수집된 기사가 없습니다.</p>",
    )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(page, encoding="utf-8")

    FONT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for font_file in FONT_SRC_DIR.glob("NotoSerifKR-*.woff2"):
        shutil.copy2(font_file, FONT_OUT_DIR / font_file.name)

    print(f"생성 완료 -> {OUT_FILE}")


if __name__ == "__main__":
    main()
