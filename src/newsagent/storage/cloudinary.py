from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from newsagent.config import get_settings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def upload(path: Path) -> str:
    s = get_settings()
    with path.open("rb") as f:
        r = httpx.post(
            f"https://api.cloudinary.com/v1_1/{s.cloudinary_cloud}/image/upload",
            data={"upload_preset": s.cloudinary_preset},
            files={"file": (path.name, f, "image/jpeg")},
            timeout=60,
        )
    r.raise_for_status()
    return r.json()["secure_url"]
