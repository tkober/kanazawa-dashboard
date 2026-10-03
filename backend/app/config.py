"""Loading and validating the dashboard configuration (apps.yaml).

The file is re-read whenever its modification time changes, so a mounted
config can be edited on the server without restarting the container.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "apps.yaml"


def config_path() -> Path:
    return Path(os.environ.get("APPS_CONFIG", DEFAULT_CONFIG))


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class App:
    id: str
    name: str
    url: str
    health_url: str
    description: str | None = None
    icon: str | None = None
    group: str | None = None


@dataclass(frozen=True)
class Dashboard:
    title: str
    apps: tuple[App, ...]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _require_http_url(value: str, field: str, app_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ConfigError(f"{app_name}: '{field}' must be an absolute http(s) URL, got {value!r}")
    return value


def parse(raw: object) -> Dashboard:
    if not isinstance(raw, dict):
        raise ConfigError("apps.yaml must be a mapping with an 'apps' list")
    entries = raw.get("apps")
    if not isinstance(entries, list) or not entries:
        raise ConfigError("apps.yaml needs a non-empty 'apps' list")

    apps: list[App] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"apps[{i}] must be a mapping")
        name = entry.get("name")
        url = entry.get("url")
        if not name or not url:
            raise ConfigError(f"apps[{i}] needs at least 'name' and 'url'")
        name, url = str(name), str(url)
        _require_http_url(url, "url", name)

        # health: omitted → probe the app URL itself; a path → relative to
        # the app URL; an absolute URL → used as is (e.g. a separate API port).
        health = entry.get("health")
        health_url = urljoin(url, str(health)) if health else url
        _require_http_url(health_url, "health", name)

        app_id = str(entry.get("id") or _slug(name))
        if app_id in seen:
            raise ConfigError(f"duplicate app id {app_id!r} (set 'id' explicitly)")
        seen.add(app_id)

        apps.append(
            App(
                id=app_id,
                name=name,
                url=url,
                health_url=health_url,
                description=entry.get("description"),
                icon=entry.get("icon"),
                group=entry.get("group"),
            )
        )

    return Dashboard(title=str(raw.get("title") or "Dashboard"), apps=tuple(apps))


_cache: tuple[Path, float, Dashboard] | None = None


def load() -> Dashboard:
    global _cache
    path = config_path()
    mtime = path.stat().st_mtime
    if _cache is None or _cache[0] != path or _cache[1] != mtime:
        with path.open(encoding="utf-8") as f:
            _cache = (path, mtime, parse(yaml.safe_load(f)))
    return _cache[2]
