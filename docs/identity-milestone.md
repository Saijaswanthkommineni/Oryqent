# Identity milestone

## Scope and assumptions

This milestone establishes identity, tenancy, roles, and administrative boundaries. It deliberately
does not include self-registration, email invitations, password-reset email, web/mobile clients, or
examination workflows.

Assumptions:

- Institutions are created by platform administrators.
- Institution administrators create teacher and student accounts with initial passwords.
- Only platform administrators create or modify institution administrators.
- A user may hold memberships in more than one institution. Tenant access is always selected through
  an explicit institution-scoped route and verified server-side.
- Credentials are issued only after an active account presents a valid password.
- Client applications may cache membership summaries, but authorization is recalculated by the API.

## Data model

### User

- UUID primary key, casefolded unique email, full name.
- Django password hashing and configured password validators.
- `is_platform_admin` is an explicit platform capability.
- `auth_version` invalidates access and refresh tokens after a password change.
- Inactive accounts cannot authenticate.

### Institution

- UUID primary key, unique case-insensitive slug, name, status, IANA timezone, JSON settings.
- Status is `active` or `suspended`. Suspension blocks non-platform tenant access immediately.
- Settings are returned only to institution administrators and platform administrators.

### InstitutionMembership

- Unique `(user, institution)` pair.
- Role: `institution_admin`, `teacher`, or `student`.
- Active flag allows access to be revoked without deleting audit history.
- Institution deletion is protected while memberships exist.

### AuditLog

Administrative changes record actor, institution, action, target, metadata, source IP, user agent,
request ID, and timestamp. Passwords and tokens are never recorded.

## Authentication contract

### `POST /api/v1/auth/login/`

Request:

```json
{"email": "admin@example.com", "password": "..."}
```

Success `200`:

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "full_name": "Institution Admin",
    "is_platform_admin": false,
    "date_joined": "2026-11-07T00:00:00Z"
  },
  "memberships": [
    {
      "id": "membership-uuid",
      "role": "institution_admin",
      "institution": {
        "id": "institution-uuid",
        "name": "Alpha College",
        "slug": "alpha",
        "status": "active",
        "timezone": "Asia/Kolkata"
      }
    }
  ]
}
```

Only active memberships in active institutions are returned. Authentication errors intentionally do
not disclose whether an email exists.

### `POST /api/v1/auth/refresh/`

Refresh tokens rotate and the previous token is blacklisted. A refresh token is rejected if the
account is inactive or its token version no longer matches.

### `POST /api/v1/auth/logout/`

Accepts `{"refresh": "<token>"}`. The refresh token must belong to the authenticated user, then it is
blacklisted. Existing access tokens expire within 15 minutes by default; password changes revoke
access tokens immediately.

### `PATCH /api/v1/auth/me/`

Only `full_name` is mutable. Email and platform capability are not client-editable.

### `POST /api/v1/auth/password/change/`

Accepts current and new passwords. It validates the new password, increments `auth_version`, and
blacklists every outstanding refresh token in one transaction. Old access and refresh tokens then
fail immediately.

## Administrative contract

### Create institution

`POST /api/v1/institutions/` (platform administrator only):

```json
{
  "name": "Alpha College",
  "slug": "alpha",
  "timezone": "Asia/Kolkata",
  "settings": {},
  "admin": {
    "email": "admin@alpha.example",
    "full_name": "Alpha Admin",
    "password": "<validated password>"
  }
}
```

Institution, first administrator, membership, and audit events commit atomically.

### Create member

`POST /api/v1/institutions/{institution_id}/members/`:

```json
{
  "email": "teacher@alpha.example",
  "full_name": "Teacher Name",
  "role": "teacher",
  "password": "<validated password>"
}
```

Institution administrators may create `teacher` and `student`; platform administrators may also
create `institution_admin`.

### Update member

`PATCH /api/v1/institutions/{institution_id}/members/{membership_id}/`:

```json
{"role": "student", "is_active": true}
```

Every update is constrained to the institution in the URL. The final active institution
administrator cannot be demoted or deactivated.

## Error format

```json
{
  "error": {
    "code": "permission_denied",
    "message": "You do not have access to this institution.",
    "details": null
  },
  "request_id": "correlation-id"
}
```

Validation failures return field details under `error.details`.

## Verification performed

Executed on 2026-11-07:

```text
cd backend
.venv/Scripts/python manage.py makemigrations accounts institutions audit
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py test --settings=config.settings.test
.venv/Scripts/ruff check .
```

Results: migrations generated without errors; Django system check clean; 33 tests passed; Ruff clean.

Tests cover successful login, generic authentication failure, disabled accounts, membership
filtering, refresh rotation/blacklisting, logout ownership, password-change revocation, weak-password
rejection, health checks, platform-admin bootstrap, cross-tenant read/write/member/audit denial,
object-level membership isolation, role escalation denial, immediate deactivation, last-admin
protection, atomic institution creation, duplicate records, suspension, invalid timezones, audit
scope, and request correlation.
