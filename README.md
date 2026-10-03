# Kanazawa Dashboard

Eine bookmarkbare Startseite für alle Apps auf Kanazawa: eine Kachel pro App,
ein Klick öffnet die App, und ein Punkt zeigt an, ob die App gerade erreichbar
ist.

- **grün, Online**: der Health-Endpoint antwortet mit einem Status < 400
  (inkl. Antwortzeit)
- **orange, Fehler 5xx**: die App antwortet, aber mit einem Fehlerstatus
- **rot, Offline/Timeout**: keine Antwort innerhalb von 3 s

Der Status wird beim Laden, alle 30 s (solange der Tab sichtbar ist) und per
Button „Aktualisieren“ neu geprüft.

## Konfiguration: `config/apps.yaml`

Welche Apps angezeigt werden und wo sie liegen, steht in
[`config/apps.yaml`](config/apps.yaml); die Felder sind dort oben beschrieben.
Die Server-Adresse steht nur einmal im Feld `host` (eine IP, kein
`kanazawa.local`, weil mDNS-Namen über WireGuard und in Containern nicht
auflösen); in `url` und `health` wird sie per `{host}` eingesetzt. Die Datei
wird ins Backend-Image gebacken: Änderung committen, auf `main` pushen, CI
baut ein neues Image, Stack neu deployen.

Alternativ lässt sich eine Datei auf dem Server mounten (`APPS_CONFIG`, siehe
unten). Das Backend liest sie bei jeder Änderung neu ein, ein Neustart ist dann
nicht nötig.

## Architektur

```
frontend/  Angular (Standalone-Komponenten, Signals) + nginx-Image,
           das /api/ ans Backend proxyt
backend/   FastAPI mit uv: liest apps.yaml, prüft die Health-Endpoints
config/    apps.yaml
```

Die Health-Checks laufen **im Backend**, nicht im Browser: die Apps liegen auf
anderen Origins ohne CORS-Header, der Browser könnte ihren Status nicht lesen.
Deshalb muss `host` in `apps.yaml` eine Adresse sein, die auch vom
Backend-Container aus erreichbar ist.

API:

| Route             | Inhalt                                                |
|-------------------|-------------------------------------------------------|
| `GET /api/apps`   | Titel und Apps aus `apps.yaml` (ohne Health-URLs)     |
| `GET /api/status` | Status je App-ID; Ergebnisse werden 10 s gecacht      |
| `GET /api/health` | Health des Dashboards selbst                          |

## Deployment (compose-stacks-unraid)

```yaml
services:
  kanazawa-dashboard-backend:
    image: ghcr.io/tkober/kanazawa-dashboard-backend:latest
    container_name: kanazawa-dashboard-backend
    restart: unless-stopped
    # Erreicht die Apps über die Host-IP in apps.yaml (host: ...); kein
    # extra_hosts nötig, da kein mDNS-Name aufgelöst werden muss.
    # optional: Config auf dem Server statt im Image
    # environment:
    #   APPS_CONFIG: /config/apps.yaml
    # volumes:
    #   - ./config/apps.yaml:/config/apps.yaml:ro
    networks:
      - kanazawa-dashboard-net
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')\""]
      interval: 30s
      timeout: 5s
      retries: 5

  kanazawa-dashboard-frontend:
    image: ghcr.io/tkober/kanazawa-dashboard-frontend:latest
    container_name: kanazawa-dashboard-frontend
    restart: unless-stopped
    depends_on:
      kanazawa-dashboard-backend:
        condition: service_healthy
    ports:
      - "8087:80"
    networks:
      - kanazawa-dashboard-net

networks:
  kanazawa-dashboard-net:
    name: kanazawa-dashboard-net
```

Umgebungsvariablen des Backends: `APPS_CONFIG` (Pfad zur YAML),
`HEALTH_TIMEOUT_SECONDS` (Default 3), `HEALTH_CACHE_SECONDS` (Default 10).

## Lokal entwickeln

```bash
cd backend && uv run uvicorn app.main:app --port 8000   # liest ../config/apps.yaml
cd frontend && npm install && npx ng serve              # proxyt /api auf :8000
cd backend && uv run pytest
```
