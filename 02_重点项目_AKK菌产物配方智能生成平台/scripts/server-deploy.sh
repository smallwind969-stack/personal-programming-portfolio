#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/akk-platform}"

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  cp .env.server.example .env
  echo "Created $APP_DIR/.env from .env.server.example."
  echo "Edit .env and replace API keys before enabling LLM features."
fi

docker compose up -d --build

install -m 0644 deploy/nginx/akk-platform.conf /etc/nginx/sites-available/akk-platform.conf
ln -sf /etc/nginx/sites-available/akk-platform.conf /etc/nginx/sites-enabled/akk-platform.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

docker compose ps
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error --head http://127.0.0.1:3000
curl --fail --silent --show-error --head http://127.0.0.1
