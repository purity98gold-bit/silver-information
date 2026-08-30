#!/usr/bin/env python3
"""
config/feeds.txt 의 RSS 피드를 모두 읽어서
config/brands.txt 에 있는 브랜드/키워드가 제목이나 요약에 포함된 기사만 골라
data/articles.json 에 누적 저장한다.

새로 수집된 기사에 한해:
- RSS에 썸네일이 있으면 그대로 사용
- 없으면 기사 페이지에 접속해서 og:image / og:description을 읽어와 보강
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "config" / "feeds.txt"
BRANDS_FILE = ROOT / "config" / "brands.txt"
DATA_FILE = ROOT / "data" / "articles.json"

MAX_ARTICLES = 300       # 누적 저장 최대 개수
MAX_ENRICH_FETCHES = 30  # 한 번 실행에서 og:image/description 보강 요청을 걸 최대 건수
FETCH_TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MyFashionMagBot/1.0; personal RSS reader)"}
MIN_SUMMARY_LEN_FOR_ENRICH = 80  # 이보다 짧은 요약이면 og:description으로 보강 시도


def load_lines(path):
    if not path.exists():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def clean_html(raw):
    return re.sub(r"<[^>]+>", "", raw or "").strip()


def matched_brands(text, brands):
    text_low = text.lower()
    return [b for b in brands if b.lower() in text_low]


def load_existing():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def extract_rss_image(entry):
    """RSS 항목 안에 이미 들어있는 썸네일을 찾는다 (media:thumbnail, media:content, enclosure, 본문 내 첫 <img>)."""
    for key in ("media_thumbnail", "media_content"):
        items = entry.get(key)
        if items:
            url = items[0].get("url")
            if url:
                return url

    for link in entry.get("links", []):
        if str(link.get("type", "")).startswith("image/"):
            href = link.get("href")
            if href:
                return href

    raw_html = ""
    if entry.get("content"):
        raw_html = entry["content"][0].get("value", "")
    raw_html += entry.get("summary", "") or ""

    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_html)
    if match:
        return match.group(1)

    return None


def extract_video_thumbnail(soup):
    """og:image가 없을 때, 페이지에 삽입된 유튜브/비메오 영상의 대표 프레임(썸네일)을 대신 가져온다."""
    for tag in soup.find_all(["iframe", "embed"]):
        src = tag.get("src") or tag.get("data-src") or ""

        m = re.search(r"(?:youtube\.com/embed/|youtu\.be/)([\w-]+)", src)
        if m:
            return f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg"

        m = re.search(r"player\.vimeo\.com/video/(\d+)", src)
        if m:
            try:
                resp = requests.get(
                    f"https://vimeo.com/api/v2/video/{m.group(1)}.json",
                    headers=HEADERS, timeout=FETCH_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()[0]["thumbnail_large"]
            except Exception:
                continue

    video_tag = soup.find("video")
    if video_tag and video_tag.get("poster"):
        return video_tag["poster"]

    return None


def fetch_og_tags(url):
    """기사 페이지에 접속해서 og:image, og:description을 읽어온다.
    og:image가 없으면 삽입된 영상의 썸네일로 대체를 시도한다. 실패하면 조용히 None 반환."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        def meta(prop):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            return tag.get("content") if tag and tag.get("content") else None

        image = meta("og:image") or extract_video_thumbnail(soup)

        return {
            "image": image,
            "description": meta("og:description"),
        }
    except Exception:
        return {"image": None, "description": None}


def main():
    feeds = load_lines(FEEDS_FILE)
    brands = load_lines(BRANDS_FILE)

    if not feeds:
        print("feeds.txt에 등록된 피드가 없습니다.", file=sys.stderr)
        sys.exit(1)

    existing = load_existing()
    existing_links = {a["link"] for a in existing}
    new_items = []

    for feed_url in feeds:
        print(f"[fetch] {feed_url}")
        parsed = feedparser.parse(feed_url)
        source_name = parsed.feed.get("title", feed_url)

        for entry in parsed.entries:
            link = entry.get("link")
            if not link or link in existing_links:
                continue

            title = entry.get("title", "").strip()
            summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
            full_text = f"{title} {summary}"

            tags = matched_brands(full_text, brands) if brands else []

            # brands.txt가 비어있으면 전부 포함, 채워져 있으면 매칭된 것만 포함
            if brands and not tags:
                continue

            published = entry.get("published", "") or entry.get("updated", "")
            image_url = extract_rss_image(entry)

            new_items.append({
                "title": title,
                "link": link,
                "summary": summary[:600],
                "source": source_name,
                "published": published,
                "matched_brands": tags,
                "image": image_url,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
            existing_links.add(link)

    # 새 기사 중 이미지가 없거나 요약이 짧은 항목에 한해 og 태그로 보강 (요청 수 제한)
    enrich_count = 0
    for item in new_items:
        if enrich_count >= MAX_ENRICH_FETCHES:
            break
        needs_image = not item["image"]
        needs_summary = len(item["summary"]) < MIN_SUMMARY_LEN_FOR_ENRICH
        if not (needs_image or needs_summary):
            continue

        og = fetch_og_tags(item["link"])
        if needs_image and og["image"]:
            item["image"] = og["image"]
        if needs_summary and og["description"]:
            item["summary"] = og["description"][:600]
        enrich_count += 1

    if enrich_count:
        print(f"og:image/description 보강 요청 {enrich_count}건 수행")

    combined = new_items + existing
    combined = combined[:MAX_ARTICLES]

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"새 기사 {len(new_items)}건 추가, 총 {len(combined)}건 저장됨 -> {DATA_FILE}")


if __name__ == "__main__":
    main()
