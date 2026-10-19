import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from newsagent.config import get_settings

BASE = "https://graph.instagram.com/v21.0"  # verify the current version in Meta docs


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def _post(path: str, data: dict) -> dict:
    s = get_settings()
    r = httpx.post(f"{BASE}/{path}", data={**data, "access_token": s.ig_token}, timeout=60)
    if r.is_error:
        raise RuntimeError(f"IG API {r.status_code}: {r.text}")
    return r.json()


def _wait_ready(container_id: str, timeout: int = 120) -> None:
    s = get_settings()
    end = time.time() + timeout
    while time.time() < end:
        r = httpx.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code", "access_token": s.ig_token},
            timeout=30,
        )
        status = r.json().get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container failed: {r.text}")
        time.sleep(3)
    raise TimeoutError("Container not ready in time")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    uid = get_settings().ig_user_id
    children = [
        _post(f"{uid}/media", {"image_url": u, "is_carousel_item": "true"})["id"]
        for u in image_urls
    ]
    for c in children:
        _wait_ready(c)
    container = _post(
        f"{uid}/media",
        {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption},
    )["id"]
    _wait_ready(container)
    return _post(f"{uid}/media_publish", {"creation_id": container})["id"]
