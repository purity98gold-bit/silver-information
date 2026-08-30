#!/usr/bin/env python3
"""docs/instagram/ 안의 날짜별 카드 폴더들을 훑어서 갤러리 index.html을 만든다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IG_DIR = ROOT / "docs" / "instagram"

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Silver Information · 인스타그램 카드</title>
<style>
  @font-face {{ font-family: "Noto Serif KR"; font-weight: 700; src: url("../assets/fonts/NotoSerifKR-Bold.woff2") format("woff2"); font-display: swap; }}
  :root {{ --bg:#0a0a0a; --ink:#f2f2f0; --muted:#8a8a85; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Pretendard","Apple SD Gothic Neo",sans-serif; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:32px 20px 64px; }}
  a.back {{ color:var(--muted); font-size:13px; text-decoration:none; }}
  h1 {{ font-family:"Noto Serif KR", serif; font-size:26px; margin:20px 0 4px; font-weight:700; }}
  h2 {{ font-size:15px; color:var(--muted); font-weight:500; margin:32px 0 12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(160px, 1fr)); gap:10px; }}
  .grid a img {{ width:100%; display:block; }}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../index.html">← 매거진으로</a>
  <h1>인스타그램 카드</h1>
{sections}
</div>
</body>
</html>
"""


def main():
    if not IG_DIR.exists():
        print("아직 생성된 카드가 없습니다.")
        return

    day_dirs = sorted([d for d in IG_DIR.iterdir() if d.is_dir()], reverse=True)

    sections = []
    for day_dir in day_dirs:
        images = sorted(day_dir.glob("*.png"))
        if not images:
            continue
        thumbs = "\n".join(
            f'    <a href="{day_dir.name}/{img.name}" target="_blank"><img src="{day_dir.name}/{img.name}" loading="lazy"></a>'
            for img in images
        )
        sections.append(f'  <h2>{day_dir.name}</h2>\n  <div class="grid">\n{thumbs}\n  </div>')

    page = PAGE_TEMPLATE.format(sections="\n".join(sections) if sections else "<p>아직 생성된 카드가 없습니다.</p>")
    (IG_DIR / "index.html").write_text(page, encoding="utf-8")
    print(f"갤러리 생성 완료 -> {IG_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
