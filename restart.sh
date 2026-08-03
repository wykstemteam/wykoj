#!/bin/bash
# Rebuild the wykoj image from the current code and recreate the running container.
set -euo pipefail
cd "$(dirname "$0")"

git pull

docker network create wykoj-net 2>/dev/null || true

docker build -t wykoj .

docker stop wykoj 2>/dev/null || true
docker rm wykoj 2>/dev/null || true

docker run -d \
  --name wykoj \
  --network wykoj-net \
  -p 3000:3000 \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  -v "$(pwd)/.git:/app/.git" \
  -v "$(pwd)/test_cases:/app/test_cases" \
  wykoj

docker logs -f --tail 100 wykoj
