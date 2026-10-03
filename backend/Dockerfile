# API-only image. The Angular bundle ships in its own nginx image, which also
# reverse-proxies /api here (see frontend/nginx.conf).
#
# Build context is the repository root, not backend/: the default apps.yaml in
# config/ lives outside this directory and gets baked in.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY config/apps.yaml ./config/apps.yaml

# APPS_CONFIG can point at a mounted file instead; it is re-read whenever it
# changes, so editing a mounted config needs no restart.
ENV APPS_CONFIG=/app/config/apps.yaml \
    HOST=0.0.0.0 \
    PORT=8000
EXPOSE 8000

# Shell form so $HOST/$PORT expand at runtime (exec'd via `sh -c`, so uvicorn
# still becomes PID 1's child and receives signals).
CMD ["sh", "-c", "exec uv run uvicorn app.main:app --host \"$HOST\" --port \"$PORT\""]
