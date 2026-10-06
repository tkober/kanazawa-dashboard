from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Response

from . import config, health

app = FastAPI(title="Kanazawa Dashboard")


def _dashboard() -> config.Dashboard:
    try:
        return config.load()
    except (OSError, config.ConfigError) as exc:
        raise HTTPException(status_code=500, detail=f"invalid apps config: {exc}") from exc


@app.get("/api/health")
async def own_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/apps")
async def apps(response: Response) -> dict:
    # Allow cross-origin reads of this one route: the Japanese learning apps
    # (other origins/ports) show an app switcher that fetches this list from
    # the browser (see sumi-ui concept doc, "App-Umschalter"). The list is
    # read-only and never contains health URLs, so a wildcard is fine here;
    # /api/status and /api/health intentionally stay without CORS headers.
    # A plain GET needs no preflight, so setting the header on this response
    # is enough — no need for CORSMiddleware on the whole app.
    response.headers["Access-Control-Allow-Origin"] = "*"
    dashboard = _dashboard()
    return {
        "title": dashboard.title,
        # health_url stays server-side: it may be an internal address.
        "apps": [
            {k: v for k, v in asdict(a).items() if k != "health_url"} for a in dashboard.apps
        ],
    }


@app.get("/api/status")
async def status() -> dict:
    statuses = await health.check_all(_dashboard().apps)
    return {app_id: asdict(s) for app_id, s in statuses.items()}
