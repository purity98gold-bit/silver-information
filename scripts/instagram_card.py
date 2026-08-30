#!/usr/bin/env python3
"""
data/articles.json 중 최근 새로 수집된 기사마다
1080x1080 인스타그램용 텍스트 카드(다크 톤)를 만든다.

산출물: docs/instagram/<날짜>/<n>.png
"""
import json
import re
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "articles.json"
FONT_BOLD = ROOT / "assets" / "fonts" / "Pretendard-Bold.otf"
FONT_REGULAR = ROOT / "assets" / "fonts" / "Pretendard-Regular.otf"
OUT_DIR = ROOT / "docs" / "instagram"

RECENT_HOURS = 30       # 이 시간 내 수집된 기사만 카드로 만듦
MAX_CARDS_PER_RUN = 20  # 한 번 실행에 만들 카드 수 상한

SIZE = 1080
BG = (10, 10, 10)          # 거의 블랙
FG = (245, 245, 240)       # 오프화이트
MUTED = (140, 140, 135)    # 회색 (출처/브랜드 태그용)
MARGIN = 90


def load_recent_articles():
    if not DATA_FILE.exists():
        return []
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
    return recent[:MAX_CARDS_PER_RUN]


def wrap_text(draw, text, font, max_width):
    """주어진 폭에 맞춰 텍스트를 여러 줄로 감싼다 (한글 대응, 픽셀 폭 기준)."""
    lines = []
    for paragraph in text.split("\n"):
        words = list(paragraph)  # 한글은 어절보다 글자 단위 wrap이 안정적
        current = ""
        for ch in words:
            test = current + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = ch
            else:
                current = test
        lines.append(current)
    return lines


def fit_font_size(draw, text, font_path, max_width, max_height, start_size=76, min_size=36):
    """텍스트가 카드 안에 들어가도록 폰트 크기를 줄여가며 맞춘다."""
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(str(font_path), size)
        lines = wrap_text(draw, text, font, max_width)
        line_height = int(size * 1.35) + 14
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, lines, line_height
        size -= 4
    font = ImageFont.truetype(str(font_path), min_size)
    lines = wrap_text(draw, text, font, max_width)
    line_height = int(min_size * 1.35) + 14
    return font, lines, line_height


def make_card(article, brand_label):
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    max_text_width = SIZE - MARGIN * 2
    title = article.get("title", "").strip()

    title_font, title_lines, line_height = fit_font_size(
        draw, title, FONT_BOLD, max_text_width, max_height=560
    )

    total_text_height = line_height * len(title_lines)
    start_y = (SIZE - total_text_height) // 2

    y = start_y
    for line in title_lines:
        draw.text((MARGIN, y), line, font=title_font, fill=FG)
        y += line_height

    # 상단: 브랜드 태그
    small_font = ImageFont.truetype(str(FONT_REGULAR), 32)
    if brand_label:
        draw.text((MARGIN, 80), brand_label.upper(), font=small_font, fill=MUTED)

    # 하단: 출처 + 워터마크
    source = article.get("source", "")
    footer_font = ImageFont.truetype(str(FONT_REGULAR), 30)
    draw.text((MARGIN, SIZE - 130), source, font=footer_font, fill=MUTED)
    draw.text((MARGIN, SIZE - 90), "Silver Information", font=footer_font, fill=MUTED)

    return img


def slugify(text, maxlen=40):
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    text = re.sub(r"\s+", "-", text)
    return text[:maxlen] or "card"


def main():
    if not FONT_BOLD.exists() or not FONT_REGULAR.exists():
        raise SystemExit("assets/fonts에 Pretendard 폰트 파일이 없습니다.")

    articles = load_recent_articles()
    if not articles:
        print("최근 새로 수집된 기사가 없어 카드를 생성하지 않습니다.")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_dir = OUT_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for article in articles:
        brand_label = ", ".join(article.get("matched_brands", [])[:2])
        img = make_card(article, brand_label)
        filename = f"{count+1:02d}-{slugify(article.get('title',''))}.png"
        out_path = day_dir / filename
        img.save(out_path, "PNG")
        count += 1

    print(f"인스타그램 카드 {count}장 생성 완료 -> {day_dir}")


if __name__ == "__main__":
    main()
