#!/usr/bin/env python3
"""
data/articles.json 중 최근 수집된 기사들을 골라
config/style_samples.md 의 말투를 참고해서
내 어투로 쓴 콘텐츠 초안(digest)을 만든다.

Gemini에게 자유 텍스트가 아니라 "각 소식당 문단 하나"의 구조화된 JSON을
받아서, 우리가 직접 각 문단에 그 소식의 이미지/링크를 붙인다.
메인 매거진 페이지와 동일한 비주얼(피처드 1개 + 리스트)을 그대로 사용해서
일관된 인터페이스를 유지한다.

GEMINI_API_KEY 환경변수가 없으면 조용히 건너뛴다.
(Google Gemini API 무료 티어 사용 - https://aistudio.google.com/apikey 에서 발급)
"""
import html
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "articles.json"
STYLE_FILE = ROOT / "config" / "style_samples.md"
DRAFTS_DIR = ROOT / "docs" / "drafts"

GEMINI_MODEL = "gemini-flash-lite-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

RECENT_HOURS = 30  # 이 시간 내에 수집된 기사만 오늘의 초안 대상으로 삼음
MAX_ITEMS_FOR_DRAFT = 12

SYSTEM_PROMPT = """당신은 사용자의 개인 패션 매거진 에디터입니다.
아래에 사용자의 예전 블로그 글 샘플이 주어집니다. 그 문체, 어미, 호흡, 자주 쓰는 표현을
최대한 그대로 살려서, 오늘 수집된 패션 뉴스 목록을 바탕으로 소식마다 짧은 문단을 씁니다.

규칙:
- 원문 기사를 그대로 베끼지 말고 반드시 자기 말로 재구성할 것
- 각 소식은 2~4문장 정도로 짧게, 사용자의 취향/시선이 드러나게 코멘트를 곁들일 것
- 소제목이나 번호를 문단 안에 적지 말 것 (구조는 별도로 처리됨)
- 과장된 홍보 문구나 상투적인 트렌드 기사체는 피할 것
- 응답은 반드시 지정된 JSON 스키마 형식으로만 출력할 것
"""


FEATURED_ITEM_TEMPLATE = """
<a class="featured" href="{link}" target="_blank" rel="noopener">
  {image_html}
  <div class="featured-text">
    <div class="featured-tag">Today's Pick</div>
    <h2 class="featured-title">{title}</h2>
    <p class="featured-summary">{paragraph}</p>
    <div class="item-meta">{source} · {published}</div>
  </div>
</a>
"""

LIST_ITEM_TEMPLATE = """
<a class="item" href="{link}" target="_blank" rel="noopener">
  <div class="item-text">
    <h2 class="item-title">{title}</h2>
    <p class="item-summary">{paragraph}</p>
    <div class="item-meta">{source} · {published}</div>
  </div>
  {image_html}
</a>
"""

DRAFT_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Silver Information · {date} 초안</title>
<style>
  @font-face {{ font-family: "Noto Serif KR"; font-weight: 500; src: url("../assets/fonts/NotoSerifKR-Medium.woff2") format("woff2"); font-display: swap; }}
  @font-face {{ font-family: "Noto Serif KR"; font-weight: 700; src: url("../assets/fonts/NotoSerifKR-Bold.woff2") format("woff2"); font-display: swap; }}
  :root {{ --bg:#0a0a0a; --ink:#f2f2f0; --muted:#8a8a85; --line:#232323; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Pretendard","Apple SD Gothic Neo",sans-serif; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:32px 20px 80px; }}
  .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; }}
  .topbar a {{ color:var(--muted); font-size:13px; text-decoration:none; }}
  h1.page-title {{ font-family:Helvetica, Arial, sans-serif; font-size:24px; margin:0 0 4px; font-weight:700; }}
  .date {{ color:var(--muted); font-size:12px; margin-bottom:20px; }}
  #copy-btn {{
    display:inline-block; background:var(--ink); color:#0a0a0a; border:none;
    padding:10px 18px; font-size:14px; cursor:pointer; margin-bottom:28px; font-weight:600;
  }}
  #copy-btn:active {{ transform: scale(0.98); }}
  #copy-status {{ font-size:12px; color:var(--muted); margin-left:10px; }}

  .featured {{ display:block; text-decoration:none; color:inherit; padding-bottom:32px; border-bottom:1px solid var(--line); margin-bottom:8px; }}
  .featured-thumb {{ width:100%; aspect-ratio:16/9; object-fit:cover; display:block; background:#161616; margin-bottom:22px; }}
  .featured-tag {{ font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#b8b8b8; margin-bottom:10px; }}
  .featured-title {{ font-family:"Noto Serif KR", serif; font-weight:700; font-size:24px; line-height:1.35; margin:0 0 12px; color:var(--ink); }}
  .featured-summary {{ font-size:14px; color:#b0b0ab; line-height:1.7; margin:0 0 14px; }}

  .item {{ display:flex; justify-content:space-between; align-items:center; gap:20px; padding:24px 0; border-bottom:1px solid var(--line); text-decoration:none; color:inherit; }}
  #draft-content .item:last-child {{ border-bottom:none; }}
  .item-text {{ flex:1; min-width:0; }}
  .item-title {{ font-family:"Noto Serif KR", serif; font-weight:500; font-size:17px; margin:0 0 8px; color:var(--ink); }}
  .item-summary {{ font-size:13px; color:#a8a8a3; line-height:1.5; margin:0 0 10px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .item-meta {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; }}
  .item-thumb {{ width:96px; height:96px; flex-shrink:0; object-fit:cover; background:#161616; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <a href="../index.html">← 매거진으로</a>
    <a href="index.html">전체 초안 목록</a>
  </div>
  <h1 class="page-title">오늘의 매거진 초안</h1>
  <div class="date">{date}</div>
  <button id="copy-btn" onclick="copyDraft()">📋 복사하기 (티스토리에 붙여넣기)</button>
  <span id="copy-status"></span>
  <div id="draft-content">
{content_html}
  </div>
</div>
<script>
function copyDraft() {{
  const el = document.getElementById('draft-content');
  const range = document.createRange();
  range.selectNode(el);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  try {{
    document.execCommand('copy');
    document.getElementById('copy-status').textContent = '복사됨! 티스토리 편집기에 붙여넣기(Ctrl+V) 하세요.';
  }} catch (e) {{
    document.getElementById('copy-status').textContent = '복사 실패 - 수동으로 드래그해서 복사해주세요.';
  }}
  sel.removeAllRanges();
}}
</script>
</body>
</html>
"""

DRAFTS_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Silver Information · 초안 목록</title>
<style>
  :root {{ --bg:#0a0a0a; --ink:#f2f2f0; --muted:#8a8a85; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Pretendard","Apple SD Gothic Neo",sans-serif; }}
  .wrap {{ max-width:720px; margin:0 auto; padding:32px 20px 64px; }}
  a.back {{ color:var(--muted); font-size:13px; text-decoration:none; }}
  h1 {{ font-family:Helvetica, Arial, sans-serif; font-size:24px; margin:20px 0; font-weight:700; }}
  ul {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:14px; }}
  li a {{ display:block; padding:4px; color:var(--ink); text-decoration:none; font-size:15px; }}
  li a:hover {{ color:var(--muted); }}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../index.html">← 매거진으로</a>
  <h1>초안 목록</h1>
  <ul>
{items}
  </ul>
</div>
</body>
</html>
"""


def esc(s):
    return html.escape(s or "", quote=False)


def build_content_html(items, paragraphs):
    blocks = []
    for idx, (item, para) in enumerate(zip(items, paragraphs)):
        image_html = ""
        if item.get("image"):
            thumb_class = "featured-thumb" if idx == 0 else "item-thumb"
            image_html = (
                f'<img class="{thumb_class}" src="{esc(item["image"])}" alt="" '
                f'loading="lazy" onerror="this.style.display=\'none\'">'
            )

        common = dict(
            link=item.get("link", "#"),
            title=esc(item.get("title", "")),
            paragraph=esc(para),
            source=esc(item.get("source", "")),
            published=esc(item.get("published", ""))[:16],
            image_html=image_html,
        )

        if idx == 0:
            blocks.append(FEATURED_ITEM_TEMPLATE.format(**common))
        else:
            blocks.append(LIST_ITEM_TEMPLATE.format(**common))

    return "\n".join(blocks)


def write_draft_html(date_str, items, paragraphs):
    content_html = build_content_html(items, paragraphs)
    page = DRAFT_PAGE_TEMPLATE.format(
        date=date_str,
        content_html=content_html,
    )
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    html_path = DRAFTS_DIR / f"{date_str}.html"
    html_path.write_text(page, encoding="utf-8")
    return html_path


def rebuild_drafts_index():
    html_files = sorted(DRAFTS_DIR.glob("*.html"), reverse=True)
    html_files = [f for f in html_files if f.name != "index.html"]
    items = "\n".join(
        f'    <li><a href="{f.name}">{f.stem}</a></li>' for f in html_files
    )
    if not items:
        items = "    <li>아직 생성된 초안이 없습니다.</li>"
    index_page = DRAFTS_INDEX_TEMPLATE.format(items=items)
    (DRAFTS_DIR / "index.html").write_text(index_page, encoding="utf-8")


def build_user_prompt(style_text, items):
    lines = []
    for i, a in enumerate(items, 1):
        lines.append(
            f"{i}. [{a.get('source')}] {a.get('title')}\n   요약: {a.get('summary')}"
        )
    items_block = "\n".join(lines)

    return f"""[내 문체 샘플]
{style_text}

[오늘 수집된 소식 목록 - 총 {len(items)}개]
{items_block}

위 문체를 참고해서, paragraphs 배열에 정확히 {len(items)}개의 문단을 이 목록과 같은 순서로 채워줘.
paragraphs[0]은 1번 소식, paragraphs[1]은 2번 소식... 이런 식으로 1:1로 대응해야 해."""


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY가 설정되어 있지 않아 스타일 재작성 단계는 건너뜁니다.")
        return

    if not DATA_FILE.exists():
        print("articles.json이 없습니다.")
        return

    articles = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)

    recent = []
    for a in articles:
        try:
            collected = datetime.fromisoformat(a["collected_at"])
        except (KeyError, ValueError):
            continue
        if collected >= cutoff:
            recent.append(a)

    recent = recent[:MAX_ITEMS_FOR_DRAFT]

    if not recent:
        print("최근 새로 수집된 기사가 없어 초안을 생성하지 않습니다.")
        return

    style_text = STYLE_FILE.read_text(encoding="utf-8") if STYLE_FILE.exists() else ""

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user", "parts": [{"text": build_user_prompt(style_text, recent)}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 2000,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "paragraphs": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "minItems": len(recent),
                        "maxItems": len(recent),
                    }
                },
                "required": ["paragraphs"],
            },
        },
    }

    resp = None
    max_attempts = 4
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=110,
            )
            if resp.status_code >= 500 or resp.status_code == 429:
                raise requests.exceptions.HTTPError(
                    f"{resp.status_code} from Gemini", response=resp
                )
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"Gemini 호출 실패 (시도 {attempt}/{max_attempts}): {e}")
            if attempt == max_attempts:
                print("여러 번 재시도했지만 실패해서 이번 실행은 초안 생성을 건너뜁니다.")
                return
            time.sleep(5 * attempt)

    data = resp.json()

    try:
        raw_text = "".join(
            part.get("text", "")
            for part in data["candidates"][0]["content"]["parts"]
        )
        parsed = json.loads(raw_text)
        paragraphs = parsed["paragraphs"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print("Gemini 응답을 파싱하지 못했습니다:", e, data)
        return

    if len(paragraphs) != len(recent):
        print(f"문단 수({len(paragraphs)})와 소식 수({len(recent)})가 안 맞아 안전하게 짧은 쪽에 맞춥니다.")
        n = min(len(paragraphs), len(recent))
        paragraphs, recent = paragraphs[:n], recent[:n]

    if not paragraphs:
        print("Gemini가 빈 응답을 반환했습니다.")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DRAFTS_DIR / f"{today}.md"
    out_path.write_text("\n\n".join(paragraphs), encoding="utf-8")

    html_path = write_draft_html(today, recent, paragraphs)
    rebuild_drafts_index()

    print(f"초안 생성 완료 -> {out_path}")
    print(f"복사용 페이지 생성 완료 -> {html_path}")


if __name__ == "__main__":
    main()
