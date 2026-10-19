import time
from types import SimpleNamespace

from newsagent.categories import Category
from newsagent.sources import rss


def _entry(title, link):
    return {
        "title": title,
        "summary": "details",
        "link": link,
        "published_parsed": time.localtime(),
    }


def test_fetch_dedupes_and_applies_keyword_filter(monkeypatch):
    entries = [
        _entry("Firm hiring 500 engineers", "a"),
        _entry("Firm hiring 500 engineers", "b"),
        _entry("Unrelated cake recipe", "c"),
    ]
    monkeypatch.setattr(
        rss.feedparser, "parse", lambda url, agent=None: SimpleNamespace(entries=entries)
    )
    cat = Category("jobs", "JOBS", "hint", {"Feed": "https://x"}, keywords=("hiring",))
    assert [a.link for a in rss.fetch_articles(cat)] == ["a"]
