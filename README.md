# WYK Online Judge
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: yapf](https://img.shields.io/badge/code%20style-yapf-blue)](https://github.com/google/yapf)
[
    ![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)
](https://pycqa.github.io/isort/)

An online judge with tasks and contests.

Judge backend: [wykoj/wykoj-judge](https://github.com/wykoj/wykoj-judge)

Live Version: https://oj.wyk.edu.hk

UI based on [HKOI Online Judge](https://judge.hkoi.org).

Database colocated with server. Backups are made to Google Cloud Storage.

## Prerequisites
On the machine that will run the judge:

- **Docker Engine**, with the Compose v2 plugin (`docker compose`, not the
  standalone `docker-compose`) and Buildx — `Dockerfile` opens with a
  `# syntax=` directive that only BuildKit understands. Check with
  `docker compose version` and `docker buildx version`.
- **git**, for the clone and for the test cases submodule.

(P.S. Prefer the apt packages over the `docker` snap. Snap confinement restricts
bind mounts to `$HOME` and a few other paths, and `/snap/bin` is missing from
cron's `PATH`, which breaks the scheduled backup while leaving manual runs
working — a confusing pair of problems to inherit.)

Outside this repo you also need:

- **A judging backend** —
  [wykoj/wykoj-judge](https://github.com/wykoj/wykoj-judge), reachable over
  HTTP at `JUDGE_HOST`. It receives submissions and reports results back
  through this app's API, and never connects to the database.
- **A [private GitHub repo](https://github.com/wykoj/wykoj-judge) holding the test cases**, 
  added here as a submodule, with a push webhook so updates sync automatically.
- **A Google Cloud Storage bucket and service account**, for
  [Backups](#backups). The host needs `rclone` to upload to it.
  Ask Sunny for that Google Account.

[Manual installation](#manual-installation) skips Docker, in which case you
provide the runtime yourself: Python 3.10 (3.13+ is incompatible), a MySQL 8.0
server, and `sass` from npm to compile the stylesheet.

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

1. Create the shared network, once per host, since the judge backend attaches to it too.

```bash
docker network create wykoj-net
```

2. Copy `.env.example` to `.env` and fill in the MySQL passwords
   (fresh DB: generate with `openssl rand -hex 24`).
3. Point `DB_URI` in `config.json` at the database container — the host is the
   container name, resolved over the `wykoj-net` network:
   `mysql://wykoj:<MYSQL_PASSWORD>@wykoj-db/wykojdb`
4. Ask Sunny for `config.json`. (TODO: use `.env` only.)
5. Start both services:

```bash
docker compose up -d --build
docker compose logs -f wykoj
```

6. On a new database only, create the schema and default admin user:

```bash
docker compose run --rm wykoj python init_db.py
```

Access the online judge at http://localhost:3000.

`docker compose ps` reports health. The app waits for MySQL's healthcheck
before starting, so the first boot takes ~30s longer while the database
initialises.

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
`.env`.

#### Creating the bucket and credentials
(Not needed for dev, just need to restore a backup downloaded from GCP or the live server.)
Once per deployment. Needs the `gcloud` CLI, authenticated against a project
with billing enabled. Create the bucket. Pick whichever region is nearest
the server:

```bash
gcloud storage buckets create gs://wykoj-db-backups \
  --location=asia-east2 \
  --uniform-bucket-level-access \
  --public-access-prevention
```

Set how long backups are kept:

```bash
cat > /tmp/lifecycle.json <<'EOF'
{"rule": [{"action": {"type": "Delete"}, "condition": {"age": 90}}]}
EOF
gcloud storage buckets update gs://wykoj-db-backups --lifecycle-file=/tmp/lifecycle.json
```

Create the uploader service account and grant it exactly two roles (it can't delete):

```bash
PROJECT_ID=$(gcloud config get-value project)
SA="wykoj-backup@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create wykoj-backup --display-name="WYKOJ backup uploader"

gcloud storage buckets add-iam-policy-binding gs://wykoj-db-backups \
  --member="serviceAccount:${SA}" --role="roles/storage.objectCreator"
gcloud storage buckets add-iam-policy-binding gs://wykoj-db-backups \
  --member="serviceAccount:${SA}" --role="roles/storage.objectViewer"
```

Generate the key **on the server**, since that is where the backup runs:

```bash
mkdir -p ~/.config/wykoj
gcloud iam service-accounts keys create ~/.config/wykoj/gcs-sa.json \
  --iam-account="wykoj-backup@${PROJECT_ID}.iam.gserviceaccount.com"
chmod 600 ~/.config/wykoj/gcs-sa.json
```

Keep the key outside the repo. Finally, point rclone at it:

```bash
rclone config create wykgcs "google cloud storage" \
  service_account_file="$HOME/.config/wykoj/gcs-sa.json" \
  bucket_policy_only=true
```

Confirm both that uploads work and that deletes do not:

```bash
date > /tmp/probe.txt
rclone copy /tmp/probe.txt wykgcs:wykoj-db-backups
rclone ls wykgcs:wykoj-db-backups                  # probe.txt is listed

rclone delete wykgcs:wykoj-db-backups/probe.txt    # must fail with 403
```

Failed delete is the check passing.

#### Scheduling
Install the cron entry once you have confirmed a backup restores correctly
(see [Verifying a backup](#verifying-a-backup)).

Use the *user* crontab (`crontab -e`) of whoever created the credentials above
— rclone's config lives in that user's `~/.config`, and docker access comes
from their group membership, so a root or `/etc/cron.d` entry finds neither.

```cron
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin

15 3 * * * /path/to/wykoj/scripts/backup.sh 2>&1 | logger -t wykoj-backup
```

The `PATH` line is not optional if docker or rclone came from snap: cron's
default `PATH` is roughly `/usr/bin:/bin`, which excludes `/snap/bin`, and the
job fails with `docker: command not found`. Check with `command -v docker
rclone`.

`2>&1 | logger` matters too — cron emails output by default, and with no MTA
installed that output is silently discarded.

Before trusting the schedule, run the script under a cron-like environment,
which catches `PATH` problems without waiting overnight:

```bash
env -i HOME="$HOME" PATH=/usr/local/bin:/usr/bin:/bin:/snap/bin SHELL=/bin/sh \
  /path/to/wykoj/scripts/backup.sh
```

Afterwards, confirm what the script said and that cron actually fired it —
different questions:

```bash
journalctl -t wykoj-backup --since today
journalctl -u cron --since today | grep backup.sh
rclone ls wykgcs:wykoj-db-backups
```

Note dumps are named with a UTC timestamp while cron uses the system timezone,
so a 03:15 HKT run produces a file stamped `19:15Z` the previous day.

#### Verifying a backup
Do this after any change to the backup setup, and periodically thereafter: an
upload that succeeds is not proof that the dump inside it is usable.

The steps below restore into a temporary database, leaving the live one
untouched, and download the dump from the bucket rather than reading the local
copy, so that the upload and download are covered too.

```bash
set -a; source .env; set +a
DUMP=$(rclone lsf "$BACKUP_RCLONE_DEST" | tail -1)

mkdir -p /tmp/restore-test
rclone copy "$BACKUP_RCLONE_DEST/$DUMP" /tmp/restore-test/

docker exec wykoj-db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "CREATE DATABASE restore_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"

zcat "/tmp/restore-test/$DUMP" | docker exec -i wykoj-db mysql \
  -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 restore_test
```

Compare against the live database — row counts and the checksums must match.
The checksums matter most: they compare the stored bytes of Chinese names
directly. Reading the names off a terminal proves nothing, because the
terminal's own encoding and fonts can hide a real mismatch or invent one that
is not there.

```bash
for DB in wykojdb restore_test; do
  docker exec wykoj-db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    --default-character-set=utf8mb4 -N -s -e \
    "SELECT '$DB', COUNT(*), SUM(CRC32(name)), SUM(CRC32(english_name)) FROM user;" "$DB"
done

docker exec wykoj-db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE restore_test;"
rm -rf /tmp/restore-test
```

For a real recovery, `scripts/restore.sh <dump.sql.gz>` replaces the live
database instead — it asks you to type the database name first.

#### If a backup fails
| Symptom | Cause |
|---|---|
| `BACKUP_RCLONE_DEST: not set in .env` | Destination missing from `.env` |
| `docker: command not found` under cron | `PATH` lacks `/snap/bin` |
| `didn't find section in config file` | cron is running as a user with no rclone remote |
| 403 on upload | Service account key or role bindings wrong |
| `dump is truncated, refusing to ship or prune` | mysqldump died mid-run; the `.CORRUPT` file is kept for inspection, and nothing was pruned |

A failed upload never prunes local dumps — the script confirms the object
exists remotely first, because `rclone copy` exits 0 even when it uploads
nothing.

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
