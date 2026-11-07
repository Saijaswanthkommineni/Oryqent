# Foundation audit report

Date: 2026-11-07

## Scope

The audit inspected the repository as it exists, including backend configuration, migrations, tests,
dependency resolution, Git state, Docker/Compose/Nginx configuration, environment templates, and
documentation. Web and mobile directories were checked for the expected scaffold.

No feature development was started.

## Repository inventory

Present:

- `backend/`: Django 6.1.3, DRF, SimpleJWT, PostgreSQL driver, tests, migrations.
- `infrastructure/`: Dockerfile and Nginx configuration.
- `docker-compose.yml`, `.env.example`, `.dockerignore`, `.gitignore`.
- `docs/`: architecture, security, deployment, backup/restore, roadmap.

Absent:

- `apps/web/` and any `package.json`.
- `apps/mobile/` and any `pubspec.yaml`.
- Flutter SDK.
- CI configuration.
- Python static type-checker configuration.
- PostgreSQL server or `psql` binary on this machine.
- Running Docker daemon.

The missing web/mobile projects were not created as part of this audit because doing so would be new
feature work and could not be verified against nonexistent frontend requirements.

## Checks executed and actual results

| Check | Result |
| --- | --- |
| `python manage.py check` | Passed, no issues |
| `python manage.py test --settings=config.settings.test` | **39 tests passed** |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python -m pip check` | No broken requirements |
| `python -m compileall -q apps config` | Passed |
| `ruff format --check .` | Passed |
| `ruff check .` | Passed |
| Production `manage.py check --deploy` with valid configuration | Passed, no issues |
| Production checks with placeholder/undersized secret | Failed closed as required |
| Production checks with wildcard allowed host | Failed closed as required |
| Production checks with placeholder database password | Failed closed as required |
| Production checks with wildcard CORS origin | Failed closed as required |
| `docker compose config --quiet` | Passed |
| Django development server smoke test | Passed; `/health/` returned 200 with database and cache both `ok` |
| Git repository integrity (`git fsck`) | Passed |
| Tracked secret scan | Only `.env.example` placeholders found |
| Operational file line endings | LF in index and working tree |

## Verified findings repaired

### 1. Placeholder production secret was accepted

Before the repair, a copied `.env.example` secret caused only Django warning `security.W009`; the
application still started. A production deployment with a known template secret would be
compromised.

Now production rejects secrets that are shorter than 50 characters, have fewer than five unique
characters, start with `django-insecure-`, or contain template markers.

### 2. Wildcard allowed hosts were accepted

`DJANGO_ALLOWED_HOSTS=*` loaded without error. Production now rejects wildcard host entries.

### 3. Placeholder database password was accepted

The template database password could be used verbatim. Production now rejects known template
markers in `POSTGRES_PASSWORD`.

### 4. Wildcard CORS/CSRF origins were accepted

Production now rejects a bare `*` in `CORS_ALLOWED_ORIGINS` or `CSRF_TRUSTED_ORIGINS`.

### 5. Gunicorn trusted forwarding headers from every peer by default

`forwarded_allow_ips` defaulted to `*`. It now defaults to `127.0.0.1`. The local Compose profile
explicitly trusts its internal Nginx service because the backend port is not published. Other
deployments must set `GUNICORN_FORWARDED_ALLOW_IPS` to the trusted proxy address.

Regression coverage was added in `backend/config/tests/test_production_settings.py`, increasing the
suite from 33 to 39 tests.

## Checks not executable in this environment

- **Next.js lint/build:** no `apps/web/package.json` exists.
- **Flutter analysis/tests:** no Flutter SDK and no `apps/mobile/pubspec.yaml`.
- **Docker image build and service health checks:** the Docker daemon is not running
  (`docker build` exited 1 with a daemon-connection error).
- **Docker base-image manifest verification:** `docker manifest inspect` timed out.
- **Nginx configuration syntax:** no local Nginx binary or Docker daemon.
- **PostgreSQL-specific migrations and integration:** no PostgreSQL server or `psql`.
- **Gunicorn config check on Windows:** Gunicorn cannot import `fcntl` on Windows. The Docker target
  is Linux, but the container could not be built for verification.
- **Hadolint:** not installed.

These are environment limitations, not passes.

## Residual foundation gaps

- Web and mobile clients are not scaffolded, so their dependency compatibility, lint, build, tests,
  and API-contract integration cannot be assessed.
- The backend has not been exercised against PostgreSQL in this environment.
- No Python static type checker is configured.
- No CI workflow enforces the checks above.
- No load test has been run.

## Foundation status

The implemented backend foundation is stable under the checks available here. Feature development
should still wait until the web/mobile scaffolds exist and the container/PostgreSQL checks can be
run on a Docker-capable machine.
