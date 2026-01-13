#!/usr/bin/env bash
set -euo pipefail

EMAIL="you@example.com"
DOMAINS=(-d "beshtashta.kg" -d "www.beshtashta.kg")

cd "$(dirname "$0")/.."

# Стартуем HTTP nginx (без 443), чтобы пройти ACME challenge
docker compose up -d --build nginx backend db redis

# Выпускаем сертификат
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  "${DOMAINS[@]}" \
  --agree-tos --no-eff-email -m "$EMAIL"

# Перезапускаем nginx уже с SSL-оверрайдом
docker compose -f docker-compose.yml -f docker-compose.ssl.override.yml up -d nginx

echo "OK: SSL enabled"
