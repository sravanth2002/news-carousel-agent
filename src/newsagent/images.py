import html
import io
import logging
import re

import httpx
from PIL import Image

from newsagent.config import get_settings
from newsagent.models import Slide

log = logging.getLogger("newsagent")
UA = {"User-Agent": "newsagent/0.1 (personal news carousel project)"}


def _download(url: str) -> Image.Image:
    r = httpx.get(url, timeout=30, follow_redirects=True, headers=UA)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _og_image(page_url: str) -> str:
    r = httpx.get(page_url, timeout=20, follow_redirects=True, headers=UA)
    r.raise_for_status()
    for tag in re.findall(r"<meta[^>]+>", r.text[:200_000], flags=re.I):
        if re.search(r"""property=["']og:image["']""", tag, flags=re.I):
            m = re.search(r"""content=["']([^"']+)["']""", tag, flags=re.I)
            if m:
                return html.unescape(m.group(1))
    return ""


def _from_article(slide: Slide) -> tuple[Image.Image, str] | None:
    url = _og_image(slide.link) if slide.link else ""
    url = url or slide.image_url
    if not url:
        return None
    img = _download(url)
    if min(img.size) < 400:  # too small, would look blurry
        return None
    return img, "  |  Image: publisher"


def _from_commons(query: str) -> tuple[Image.Image, str] | None:
    r = httpx.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": 6,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1000,
        },
        headers=UA,
        timeout=30,
    )
    r.raise_for_status()
    pages = sorted(
        r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)
    )
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if not info.get("thumburl") or not lic or "non" in lic.lower():
            continue
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()[:25]
        try:
            return _download(info["thumburl"]), f"  |  Photo: {artist or 'Wikimedia'}, {lic}"
        except (httpx.HTTPError, OSError):
            continue
    return None


def get_image(slide: Slide, slot: int = 0) -> tuple[Image.Image | None, str]:
    mode = get_settings().image_source  # auto | article | commons | none
    steps = []
    if mode in ("auto", "article"):
        steps.append(("article", lambda: _from_article(slide)))
    if mode in ("auto", "commons"):
        steps.append(
            (
                "commons",
                lambda: (
                    (slide.subject and _from_commons(slide.subject))
                    or _from_commons(slide.keywords)
                ),
            )
        )
    for name, fn in steps:
        try:
            res = fn()
            if res:
                log.info("Image via %s for '%s'", name, slide.headline[:40])
                return res
        except (httpx.HTTPError, OSError) as e:
            log.warning("%s image failed for '%s': %s", name, slide.headline[:40], e)
    return None, ""
