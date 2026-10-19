import html
import logging
import re
import time

import feedparser

from newsagent.categories import Category
from newsagent.models import Article

log = logging.getLogger("newsagent")
UA = "Mozilla/5.0 (newsagent/0.1)"


def _clean(t: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()


def _image(e) -> str:
    for key in ("media_content", "media_thumbnail"):
        items = e.get(key) or []
        if items and items[0].get("url"):
            return items[0]["url"]
    for enc in e.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href", "")
    return ""


def fetch_articles(cat: Category, per_feed: int = 10, max_age_h: int = 72) -> list[Article]:
    items: list[Article] = []
    seen: set[str] = set()
    for source, url in cat.feeds.items():
        entries = feedparser.parse(url, agent=UA).entries[:per_feed]
        if not entries:
            log.warning("Feed empty or blocked: %s (%s)", source, url)
        for e in entries:
            title = _clean(e.get("title"))
            summary = _clean(e.get("summary"))[:500]
            text = f"{title} {summary}".lower()
            key = re.sub(r"\W+", "", title.lower())[:60]
            if not title or key in seen:
                continue
            if cat.keywords and not any(k in text for k in cat.keywords):
                continue
            seen.add(key)
            # ts = time.mktime(e.published_parsed) if e.get("published_parsed") else time.time()
            parsed = e.get("published_parsed")
            ts = time.mktime(parsed) if parsed else time.time()
            items.append(
                Article(
                    title=title,
                    link=e.get("link", ""),
                    source=source,
                    summary=summary,
                    image_url=_image(e),
                    ts=ts,
                )
            )
    items.sort(key=lambda a: -a.ts)
    recent = [a for a in items if a.ts >= time.time() - max_age_h * 3600]
    return (recent or items)[:8]
