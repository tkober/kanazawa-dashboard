"""Server-side health probes.

The browser can't do these itself: the apps live on other origins without
CORS headers, so a fetch from the dashboard page would never see the status.
"""

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Literal

import httpx

from .config import App

State = Literal["up", "unhealthy", "down"]

TIMEOUT_SECONDS = float(os.environ.get("HEALTH_TIMEOUT_SECONDS", "3"))
# Several open tabs (or a quick reload) share one round of probes.
CACHE_SECONDS = float(os.environ.get("HEALTH_CACHE_SECONDS", "10"))


@dataclass(frozen=True)
class Status:
    state: State
    http_status: int | None
    latency_ms: int | None
    error: str | None
    checked_at: float


async def probe(client: httpx.AsyncClient, url: str) -> Status:
    started = time.monotonic()
    try:
        response = await client.get(url)
    except httpx.TimeoutException:
        return Status("down", None, None, "timeout", time.time())
    except httpx.HTTPError as exc:
        return Status("down", None, None, type(exc).__name__, time.time())
    latency = round((time.monotonic() - started) * 1000)
    # Redirects count as up: an app answering at all with a redirect (e.g. to
    # a login page) is reachable, and following it could leave the host.
    state: State = "up" if response.status_code < 400 else "unhealthy"
    return Status(state, response.status_code, latency, None, time.time())


_cache: dict[str, Status] = {}
_lock = asyncio.Lock()


async def check_all(apps: tuple[App, ...]) -> dict[str, Status]:
    async with _lock:
        now = time.time()
        stale = [a for a in apps if (s := _cache.get(a.health_url)) is None or now - s.checked_at >= CACHE_SECONDS]
        if stale:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
                results = await asyncio.gather(*(probe(client, a.health_url) for a in stale))
            for app, status in zip(stale, results):
                _cache[app.health_url] = status
        return {a.id: _cache[a.health_url] for a in apps}


def clear_cache() -> None:
    _cache.clear()
