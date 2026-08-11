# WYK Online Judge
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: yapf](https://img.shields.io/badge/code%20style-yapf-blue)](https://github.com/google/yapf)
[
    ![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)
](https://pycqa.github.io/isort/)

An online judge with tasks and contests.
<br>
Judge backend: [wykoj/wykoj-judge](https://github.com/wykoj/wykoj-judge)

Live Version: https://oj.wyk.edu.hk

UI based on [HKOI Online Judge](https://judge.hkoi.org).

## Setup
Required either way. Afterwards follow [Installation](#installation) below, or
[Manual installation](#manual-installation) if you are not using Docker.

- Clone repo with `git clone https://github.com/wykstemteam/wykoj`.
- Create a (private) GitHub repo to store test cases. It will be used as a submodule.
  - Run `git submodule add [repo link] wykoj/test_cases` #
  - Run `git submodule init && git submodule update`
  - Create a webhook for just the push event #
    - Payload URL: `[your domain]/github/push`
    - Content type: `application/json`
    - Secret: `SECRET_KEY` from `config.json`
    - Events: `push` only
- Create `config.json` with the following keys: *
  - `TEST_CASES_GITHUB` - Test cases GitHub repo URL.
  - `JUDGE_HOST` - Domain of judging backend, e.g. `https://example.com` (without trailing slash).
  - `SECRET_KEY` - A URL-safe secret key, can be generated with `secrets.token_hex(16)`.
  - `DB_URI` - A database URI including login credentials. With the Docker
    setup below this points at the `wykoj-db` container, e.g.
    `mysql://wykoj:<password>@wykoj-db/wykojdb`.
  - `SLOW_REQUEST_THRESHOLD_MS` (optional) - Requests slower than this many milliseconds are logged as warnings. Defaults to `1000`.

## Installation
`docker-compose.yml` runs the app together with its own MySQL instance. It
compiles `style.min.css` and installs dependencies for you, on Python 3.10
(tortoise-orm/aiomysql are incompatible with Python 3.13+).

The database runs as a container on the same host rather than on a remote
server, so a query costs ~0.2ms instead of a network round trip.

`config.json` and the `test_cases` submodule (including `.git`, so the judge can
pull test case updates) are not baked into the image, since they contain secrets
and private repo credentials — complete [Setup](#setup) first.

1. Create the shared network, once per host. It is declared `external` in
   `docker-compose.yml` because the judge backend attaches to it too, so it
   outlives any single project:

```bash
docker network create wykoj-net
```

2. Copy `.env.example` to `.env` and fill in the MySQL passwords
   (generate with `openssl rand -hex 24`).
3. Point `DB_URI` in `config.json` at the database container — the host is the
   container name, resolved over the `wykoj-net` network:
   `mysql://wykoj:<MYSQL_PASSWORD>@wykoj-db/wykojdb`
4. Start both services:

```bash
docker compose up -d --build
docker compose logs -f wykoj
```

5. On a new database only, create the schema and default admin user:

```bash
docker compose run --rm wykoj python init_db.py
```

Access the online judge at http://localhost:3000.

`docker compose ps` reports health. The app waits for MySQL's healthcheck
before starting, so the first boot takes ~30s longer while the database
initialises.

MySQL publishes no ports — it is reachable only from the `wykoj-net` network,
not from the host or the internet.

### Upgrading from the older single-container deployment
Earlier versions ran a single container started by `restart.sh`, which compose
replaces. The existing `wykoj-net` is reused as-is, so step 1 can be skipped.

Stop and remove the old container first — it and the compose service both use
the name `wykoj`:

```bash
docker stop wykoj && docker rm wykoj
docker compose up -d --build
```

If `docker compose up` reports `network wykoj-net declared as external, but
could not be found`, the network does not exist on this host; create it with
step 1.

### Backups
`scripts/backup.sh` dumps the database, verifies the dump is complete, and
ships it off the server; `scripts/restore.sh` restores one.

Destination is Google Cloud Storage via rclone, set by `BACKUP_RCLONE_DEST` in
`.env`. One-off setup on the server:

```bash
rclone config create wykgcs "google cloud storage" \
  service_account_file="$HOME/.config/wykoj/gcs-sa.json" \
  bucket_policy_only=true
```

The uploader service account holds `objectCreator` + `objectViewer` only — it
can write new backups and read them back, but cannot delete or overwrite
existing ones, so a compromised server cannot destroy backup history. Remote
retention is consequently a bucket lifecycle rule rather than something this
script does. Keep the key outside the repo (`~/.config/wykoj/`), since
`.gitignore` matches `config.json` and `.env` by name and would not catch it.

Install the cron entry once a restore has been rehearsed:

```
15 3 * * * /path/to/wykoj/scripts/backup.sh 2>&1 | logger -t wykoj-backup
```

## Manual installation
The pre-Docker way of running the judge, kept for local development. You supply
your own MySQL instance and point `DB_URI` at it. Complete [Setup](#setup)
first.

- Compile (and minify) `wykoj/scss/style.scss` to `wykoj/static/style.min.css`.
  (Settings are configured for the VS Code
  [Live SASS Compiler](https://marketplace.visualstudio.com/items?itemName=ritwickdey.live-sass) extension.)
  - Alternative: `npm install -g sass` and `sass wykoj/scss/style.scss wykoj/static/style.min.css`
- Install/Upgrade dependencies: `pip install -r requirements.txt`.
- Initialize database: `python init_db.py`. (You will be asked to install the appropriate
  [database driver](https://tortoise-orm.readthedocs.io/en/latest/getting_started.html).)
  - An admin user with username `admin` and password `adminadmin` will be created.
    (Please change username and password upon first login.)
- Run `pyenv local wykoj` or similar to activate a python environment.
- Run `uvicorn --host 0.0.0.0 --port 3000 --factory --loop asyncio "wykoj:create_app"`

Access the online judge at http://localhost:3000.

Use Python 3.10 — tortoise-orm 0.19.1 / aiomysql 0.3.2 are incompatible with
Python 3.13+'s `asyncio.timeout()` changes.

### Note
If you are part of the WYKOJ Team: <br>
*: Ask me for `config.json`. <br>
#: You have access to `wyk-stem-team/wykoj-test-cases`, skip this step.

View the [Internal Deployment Guide](https://github.com/wykstemteam/wykoj/wiki/Internal-Deployment-Guide).

### Formatting
```bash
yapf -ri . && isort .
```

## Issues
Multiple submissions from the same user to the same task are marked `first_solve=True`.
Drop `first_solve` and `solves` columns and compute first solve instead.
Or use locks when saving submissions instead.

## Roadmap
- Spinning Ame animation on submission page if pending
- Batch user creation
- Chess rating leaderboard
- Lichess games
- Stats in user page and contests page
- Task stats page (hide link during contest, contest redirect)
- Custom page creation (admin)
- Advanced filtering form footer for submissions page
- Groups and assignments
