# Architecture

## Current shape

ORYQENT starts as a modular monolith:

- `apps.accounts`: custom identity, token authentication, account services.
- `apps.institutions`: tenant records, memberships, role permissions, administrative services.
- `apps.audit`: append-only administrative audit events.
- `config`: environment-specific settings, routing, structured logging, health checks.

The backend owns all authorization and business rules. Web and mobile clients must remain thin and
share the versioned REST contract under `/api/v1`.

## Tenancy

`Institution` is the tenant boundary. `InstitutionMembership` is the authorization link between a
user and an institution, with one of three explicit roles:

| Role | Institution administration | Member management | Own tenant access |
| --- | --- | --- | --- |
| `institution_admin` | Yes | Teachers and students only | Yes |
| `teacher` | No | No | Yes |
| `student` | No | No | Yes |

A separate boolean, `User.is_platform_admin`, grants explicitly authorized platform-wide access.
It is not a membership role and is not accepted from API input.

Institution-scoped routes include the institution UUID in the URL. A permission class resolves
that UUID to an active membership on every request. A submitted institution ID is therefore a
lookup key, not an authorization claim. Platform administrators are the only users who bypass
membership resolution.

Platform-created institution administrators are the only path to a new administrative role.
Institution administrators cannot create, promote, modify, or deactivate institution administrators.

## Transactions and concurrency

Critical membership administration runs in a database transaction and locks the institution row
with `select_for_update()`. This serializes changes that could otherwise race the
last-active-administrator invariant. Membership creation for institution administrators uses the
same lock.

Membership uniqueness and case-insensitive email/slug uniqueness are also protected by database
constraints, not only serializer validation.

## Data and infrastructure

- PostgreSQL is the production database.
- Redis provides shared throttling and cache state. Production refuses to start without it.
- Celery and Django Channels are part of the target architecture but are not yet installed because
  no asynchronous or WebSocket workflow exists in this milestone.
- Nginx terminates the local HTTP stack and proxies to Gunicorn.
- Production TLS terminates at a trusted reverse proxy or load balancer.

## Dependency rationale

- **Django / Django REST Framework**: application framework and versioned API layer.
- **djangorestframework-simplejwt**: short-lived bearer tokens, refresh rotation, and blacklist
  support needed by both web and mobile clients.
- **django-cors-headers**: explicit web-origin allowlisting; mobile clients do not depend on CORS.
- **psycopg**: PostgreSQL driver required by the production database.
- **Gunicorn**: application server used by the container profile.
- **Ruff** (development only): lint and format checks.

Celery, Channels, and their transports are intentionally deferred until there is a real background
job or WebSocket workflow to implement and test. Adding infrastructure before its consumers would
create untested complexity.

## Client strategy

The Next.js web application and Flutter mobile application will both use the same versioned REST
API. Authentication uses short-lived access tokens and rotating refresh tokens. The institution
context must always be selected from the authenticated user's server-returned memberships and
validated again by the backend.

## Future module boundaries

The next backend modules should remain inside the modular monolith:

- `question_bank`
- `examinations`
- `attempts`
- `evaluation`
- `monitoring`
- `reporting`

Real-time faculty monitoring should use Channels only where a concrete live-update requirement
exists. Answer persistence, deadlines, submission, and evaluation must remain authoritative in
database-backed services regardless of client channel.
