import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest
import yaml

from app import config, health
from app.main import app


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code = {"/ok": 200, "/redirect": 302, "/broken": 500}.get(self.path, 404)
        self.send_response(code)
        if code == 302:
            self.send_header("Location", "/login")
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def upstream():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def apps_yaml(tmp_path, monkeypatch, upstream):
    path = tmp_path / "apps.yaml"
    path.write_text(
        f"""
title: Test
apps:
  - name: Healthy App
    url: {upstream}/
    health: /ok
    icon: ✅
  - name: Redirecting
    url: {upstream}/redirect
  - name: Broken
    url: {upstream}/
    health: {upstream}/broken
  - name: Gone
    url: http://127.0.0.1:1/
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("APPS_CONFIG", str(path))
    health.clear_cache()
    return path


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_apps_lists_config_without_health_urls(client, apps_yaml, upstream):
    body = (await client.get("/api/apps")).json()
    assert body["title"] == "Test"
    assert [a["id"] for a in body["apps"]] == ["healthy-app", "redirecting", "broken", "gone"]
    assert body["apps"][0] == {
        "id": "healthy-app",
        "name": "Healthy App",
        "url": f"{upstream}/",
        "description": None,
        "icon": "✅",
        "group": None,
    }


async def test_status_classifies_each_app(client, apps_yaml):
    body = (await client.get("/api/status")).json()
    assert {k: v["state"] for k, v in body.items()} == {
        "healthy-app": "up",
        "redirecting": "up",
        "broken": "unhealthy",
        "gone": "down",
    }
    assert body["broken"]["http_status"] == 500
    assert body["gone"]["error"]


async def test_config_reloads_on_change(client, apps_yaml, upstream):
    await client.get("/api/apps")
    apps_yaml.write_text(f"apps:\n  - name: Only\n    url: {upstream}/\n", encoding="utf-8")
    # Force a different mtime even on coarse-grained filesystems.
    st = apps_yaml.stat()
    os.utime(apps_yaml, (st.st_atime, st.st_mtime + 5))
    body = (await client.get("/api/apps")).json()
    assert body["title"] == "Dashboard"
    assert [a["name"] for a in body["apps"]] == ["Only"]


@pytest.mark.parametrize(
    "raw, message",
    [
        ({}, "non-empty 'apps'"),
        ({"apps": [{"name": "x"}]}, "'name' and 'url'"),
        ({"apps": [{"name": "x", "url": "kanazawa:80"}]}, "must be an absolute http"),
        ({"apps": [{"name": "a b", "url": "http://h"}, {"name": "a-b", "url": "http://h"}]}, "duplicate"),
    ],
)
def test_invalid_config_is_rejected(raw, message):
    with pytest.raises(config.ConfigError, match=message):
        config.parse(raw)


def test_shipped_config_is_valid():
    with config.DEFAULT_CONFIG.open(encoding="utf-8") as f:
        dashboard = config.parse(yaml.safe_load(f))
    assert dashboard.apps
