import json
import logging
from datetime import date
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt

from newsagent.categories import CATEGORIES, Category
from newsagent.config import get_settings
from newsagent.models import Article, Pick, Slide
from newsagent.sources.markets import market_slide
from newsagent.sources.rss import fetch_articles

log = logging.getLogger("newsagent")

PROMPT = """You are a news editor. From the numbered articles below, pick the ONE story that best
fits this topic: {hint}.
Return: id, headline (max 60 chars), body (max 200 chars, 2 short plain sentences),
subject (the main company, product, person or place in that story, 1-3 words, as written in the article).
Use ONLY facts present in the given text. Do not invent numbers.

{articles}"""


@retry(stop=stop_after_attempt(2), reraise=True)
def _ask(cat: Category, pool: list[Article]) -> Pick:
    s = get_settings()
    listing = "\n".join(f"[{i}] ({a.source}) {a.title} — {a.summary}" for i, a in enumerate(pool))
    r = httpx.post(
        f"{s.ollama_url}/api/chat",
        json={
            "model": s.ollama_model,
            "stream": False,
            "format": Pick.model_json_schema(),
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "user", "content": PROMPT.format(hint=cat.hint, articles=listing)}
            ],
        },
        timeout=600,
    )
    r.raise_for_status()
    return Pick.model_validate_json(r.json()["message"]["content"])


def _choose(cat: Category, pool: list[Article]) -> Pick:
    try:
        return _ask(cat, pool)
    except Exception as e:
        log.warning("LLM failed for %s (%s), using top article", cat.key, e)
        a = pool[0]
        return Pick(id=0, headline=a.title, body=a.summary, subject=a.title[:40])


def build_digest() -> tuple[list[Slide], str]:
    slides: list[Slide] = []
    used: set[str] = _history()
    for cat in CATEGORIES:
        if cat.key == "stocks":
            slides.append(market_slide())
            continue
        pool = [a for a in fetch_articles(cat) if a.link not in used]
        if not pool:
            log.warning("No articles for %s, skipping slide", cat.key)
            continue
        pick = _choose(cat, pool)
        a = pool[pick.id] if 0 <= pick.id < len(pool) else pool[0]
        used.add(a.link)
        slides.append(
            Slide(
                category=cat.label,
                headline=pick.headline[:70],
                body=pick.body[:260],
                source=a.source,
                link=a.link,
                image_url=a.image_url,
                subject=pick.subject or a.title[:40],
                keywords=cat.fallback,
            )
        )
        log.info("[%s] %s", cat.key, pick.headline)

    lines = "\n".join(f"{i}. {s.category.title()}: {s.headline}" for i, s in enumerate(slides, 1))
    caption = (
        f"Daily Tech, Business and India brief | {date.today():%d %b %Y}\n\n{lines}\n\n"
        "Swipe through and follow for daily updates.\n"
        "#TechNews #AI #India #StockMarket #Jobs #StudyAbroad #Startups #Cybersecurity"
    )
    return slides, caption


def _hist_path() -> Path:
    return Path(get_settings().out_dir) / "seen_links.json"


def _history() -> set[str]:
    p = _hist_path()
    return set(json.loads(p.read_text())) if p.exists() else set()


def save_history(slides: list[Slide]) -> None:
    p = _hist_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    links = list(_history()) + [s.link for s in slides if s.link]
    p.write_text(json.dumps(links[-300:]))  # keep the last 300
