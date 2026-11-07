# ORYQENT

**One platform. Every examination.**

ORYQENT is a multi-institution examination SaaS platform. This repository currently contains the
first verified backend milestone: the institution-aware identity foundation. The examination,
question-bank, web-client, and Flutter modules are **not implemented yet** and are tracked in
[`docs/roadmap.md`](docs/roadmap.md).

## Current milestone

- Custom Django user model created in the first migration.
- Institution and institution-membership models with database-level constraints.
- Explicit roles: platform administrator, institution administrator, teacher, student.
- JWT login, refresh rotation, logout, profile, and password-change endpoints.
- Password changes increment an account token version and revoke all outstanding tokens.
- Tenant resolution from server-side membership; cross-institution access is denied.
- Platform-only institution creation, with the first institution administrator created atomically.
- Institution administrators create teachers/students; only platform administrators manage
  institution administrators.
- Last-active-administrator protection under a database row lock.
- Immutable audit events for administrative institution and membership changes.
- Structured JSON logs, request correlation, scoped throttling, health checks, and production
  security settings.
- 39 automated tests covering authentication, authorization, tenant isolation, audit behavior,
  bootstrap command behavior, production fail-closed settings, and negative failure paths.

## Local development

Requires Python 3.14.

```bash
cd backend
python -m venv .venv
# Windows Git Bash:
.venv/Scripts/python -m pip install -r requirements-dev.txt
# macOS/Linux:
# .venv/bin/python -m pip install -r requirements-dev.txt

.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py create_platform_admin \
  --email platform@example.com \
  --full-name "Platform Administrator"
.venv/Scripts/python manage.py runserver
```

`create_platform_admin` prompts for the password. For non-interactive execution, set
`ORYQENT_PLATFORM_ADMIN_PASSWORD`. Passwords are never accepted as command-line arguments.

Local development uses SQLite and an ephemeral development secret. Do not use those defaults in
production.

### Tests and lint

```bash
cd backend
.venv/Scripts/python manage.py test --settings=config.settings.test
.venv/Scripts/python manage.py check
.venv/Scripts/ruff check .
```

## Docker Compose (local stack)

The Compose profile runs PostgreSQL, Redis, Django/Gunicorn, and Nginx. It is a local profile, not a
production deployment profile.

```bash
cp .env.example .env
# Replace DJANGO_SECRET_KEY, POSTGRES_PASSWORD, and other placeholders in .env.
docker compose up --build
```

Open `http://localhost:8080/health/`. Create the first platform administrator:

```bash
docker compose exec backend python manage.py create_platform_admin \
  --email platform@example.com \
  --full-name "Platform Administrator"
```

Production must use `config.settings.production` behind TLS, with externally managed secrets. See
[`docs/deployment.md`](docs/deployment.md).

## API surface

All endpoints are under `/api/v1`.

| Method | Path | Access |
| --- | --- | --- |
| POST | `/auth/login/` | Public, throttled |
| POST | `/auth/refresh/` | Public, rotated refresh token, throttled |
| POST | `/auth/logout/` | Authenticated |
| GET/PATCH | `/auth/me/` | Authenticated |
| POST | `/auth/password/change/` | Authenticated, throttled |
| GET | `/institutions/` | Authenticated; filtered to accessible institutions |
| POST | `/institutions/` | Platform administrator |
| GET | `/institutions/{id}/` | Institution member or platform administrator |
| PATCH | `/institutions/{id}/` | Institution administrator or platform administrator |
| GET/POST | `/institutions/{id}/members/` | Institution administrator or platform administrator |
| PATCH | `/institutions/{id}/members/{membership_id}/` | Institution administrator or platform administrator |
| GET | `/institutions/{id}/audit-events/` | Institution administrator or platform administrator |
| GET | `/health/` | Unauthenticated operational probe |

Access tokens are sent as `Authorization: Bearer <access>`. The institution UUID is always resolved
against an active server-side membership; roles and institution IDs from the client are never
trusted.

## Repository layout

```
backend/          Django/DRF modular monolith and tests
infrastructure/   Container and reverse-proxy configuration
docs/             Architecture, security, deployment, and roadmap
```

`apps/web` and `apps/mobile` do not exist yet. They must consume these APIs rather than duplicating
authorization or examination business rules.

## Documentation

- [Architecture](docs/architecture.md)
- [Identity milestone and API contract](docs/identity-milestone.md)
- [Security model](docs/security.md)
- [Foundation audit](docs/foundation-audit.md)
- [Deployment](docs/deployment.md)
- [Backup and restoration](docs/backup-restore.md)
- [Roadmap and known gaps](docs/roadmap.md)
