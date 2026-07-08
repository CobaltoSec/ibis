from __future__ import annotations
import httpx


def get_weekly_downloads(package: str) -> int | None:
    try:
        url = f"https://api.npmjs.org/downloads/point/last-week/{package}"
        r = httpx.get(url, timeout=8)
        if r.status_code == 200:
            return r.json().get("downloads")
    except Exception:
        pass
    return None
