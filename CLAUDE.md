# Kanazawa Dashboard

Startseite mit Kacheln für alle auf Kanazawa deployten Apps, inkl.
Erreichbarkeits-Indikator. Ursprünglicher Auftrag: Issue #1. README.md ist die
Menschen-Doku (Konfiguration, Deployment); Änderungen an Features gehören in
beide.

## Architektur

- `config/apps.yaml`: einzige Quelle für die Apps; wird ins Backend-Image
  gebacken (Build-Kontext ist daher das Repo-Root) oder per `APPS_CONFIG`
  gemountet. `config.load()` liest neu, sobald sich die mtime ändert.
- `backend/app/config.py`: Parsen und Validieren. `health` ist optional, ein
  Pfad (relativ zu `url`) oder eine absolute URL.
- `backend/app/health.py`: Probes mit httpx, parallel, ohne Redirects zu
  folgen; < 400 = `up`, sonst `unhealthy`, Verbindungsfehler/Timeout = `down`.
  Ergebnisse 10 s gecacht, damit mehrere Tabs nicht mehrfach proben.
- `backend/app/main.py`: `/api/apps` liefert die Health-URLs bewusst nicht aus.
- `frontend/`: eine Komponente (`app.ts`), Styles global in `src/styles.css`.
  Zwei getrennte Requests: Kacheln erscheinen sofort, Status kommt nach.
  Kacheln sind echte `<a href target="_blank">`, damit sie in einem neuen Tab
  öffnen und das Dashboard offen bleibt.

Health-Checks laufen serverseitig, weil der Browser ohne CORS-Header den
Status fremder Origins nicht lesen kann. Die Server-Adresse steht nur einmal
im Feld `host` in `apps.yaml` und wird als `{host}` in `url`/`health`
eingesetzt (IP statt `kanazawa.local`, weil mDNS-Namen über WireGuard und in
Containern nicht auflösen); kein `extra_hosts` mehr nötig (siehe README).

## Tests

`cd backend && uv run pytest`: echte Upstream-Server via `http.server`, kein
Mocking von httpx.
