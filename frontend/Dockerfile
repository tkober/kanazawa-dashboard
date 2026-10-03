# --- Build the Angular bundle ---------------------------------------------
FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Serve via nginx -------------------------------------------------------
FROM nginx:alpine

# nginx's entrypoint renders templates/*.template with envsubst at startup.
# envsubst only replaces variables that are set, so both need a default here.
ENV PORT=80
# host:port the /api/ location proxies to, as seen from inside this container
# (the container name on the deployment network).
ENV API_UPSTREAM=kanazawa-dashboard-backend:8000

COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist/browser /usr/share/nginx/html

EXPOSE 80
