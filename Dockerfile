# syntax=docker/dockerfile:1

# --- Stage 1: compile wykoj/scss/style.scss -> wykoj/static/style.min.css ---
FROM node:20-alpine AS scss-builder
RUN npm install -g sass
WORKDIR /app
COPY wykoj/scss wykoj/scss
RUN sass wykoj/scss/style.scss wykoj/static/style.min.css --style=compressed --no-source-map

# --- Stage 2: runtime ---
# Pin Python 3.10: tortoise-orm==0.19.1 / aiomysql==0.3.2 are incompatible with
# Python 3.13+'s asyncio.timeout() changes (see README for details).
FROM python:3.10-slim AS runtime

# git is required at runtime: wykoj/blueprints/github.py shells out to
# `git submodule foreach git pull origin master` to sync test_cases/ on startup
# and on GitHub push webhooks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=scss-builder /app/wykoj/static/style.min.css wykoj/static/style.min.css

# Not baked into the image, provide at runtime via bind mount / secret:
#   - config.json           (SECRET_KEY, DB_URI, JUDGE_HOST, TEST_CASES_GITHUB)
#   - .git + test_cases/    (private submodule checkout with pull credentials,
#                             so the git-pull background task above can run)
EXPOSE 3000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "3000", "--factory", "--loop", "asyncio", "wykoj:create_app"]
