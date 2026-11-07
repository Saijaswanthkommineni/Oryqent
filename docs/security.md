# Security model

## Trust boundaries

- All API input is untrusted.
- Client-provided roles, platform flags, user IDs, institution IDs, scores, timers, and permissions
  are never authorization claims.
- Institution authorization is resolved from an active membership row for the authenticated user.
- Platform administrators are explicitly flagged in the user record and can bypass institution
  membership for platform administration.
- The frontend is not a security boundary.

## Authentication

- Passwords use Django's configured password hasher and validators.
- Email addresses are casefolded and constrained case-insensitively.
- Access tokens default to 15 minutes; refresh tokens default to 7 days.
- Refresh tokens rotate and the previous token is blacklisted.
- Password changes increment `auth_version`; custom JWT authentication rejects older tokens
  immediately. All outstanding refresh tokens are blacklisted in the same transaction.
- Login, refresh, and password-change endpoints are throttled. Production requires Redis so limits
  are shared across workers.
- Login failures do not reveal whether an account exists.

## Authorization

Role checks are enforced in two places: view permission classes and transactional service methods.
The duplicate enforcement is intentional defense in depth.

- Institution administrators can manage only teachers and students.
- Only platform administrators create/promote/modify institution administrators.
- Membership object updates are filtered by both membership UUID and the institution UUID in the
  route.
- At least one active institution administrator must remain; the check runs while the institution
  row is locked.
- Suspended institutions deny non-platform tenant access on the next request.
- Deactivated memberships deny tenant access immediately, even while an unexpired access token
  remains cryptographically valid.

## Data protection

- Production refuses to start without an explicit secret, PostgreSQL, Redis, and allowed hosts.
- Secrets are read from environment variables and are never committed.
- Passwords are never written to logs or audit metadata.
- Audit logs record sensitive administrative actions with actor, tenant, target, request ID, and
  source metadata.
- CORS origins are allowlisted. Credentials are disabled for API CORS because clients use bearer
  tokens.
- HTTPS, secure cookies, HSTS, and proxy header handling are enabled in production settings.

## Operational controls implemented

- JSON application logs with request IDs.
- `/health/` checks database and cache connectivity without returning internal exception details.
- Scoped rate limits for credential endpoints.
- Health checks for PostgreSQL, Redis, Django, and Nginx in local Compose.
- Non-root backend container.
- Database health checking and connection health checks.
- Database constraints for tenancy, uniqueness, and referential integrity.

## Not yet implemented

- Email verification, invitations, MFA, password-reset email, and account lockout.
- Centralized error monitoring (for example Sentry) and alert routing.
- WebSocket authentication and tenant-scoped channel groups.
- Load testing at the 500-concurrent-student target.
- Tested backup restoration, which must be rehearsed before production.
- Browser-monitoring event review and examination anti-abuse controls.
- Full Content Security Policy for the web client; it depends on the final Next.js asset strategy.

These gaps must not be represented as complete. They are sequenced in
[`roadmap.md`](roadmap.md).
