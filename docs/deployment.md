# Deployment

## Local Docker Compose

Compose uses `config.settings.docker_local`, which starts from production settings but disables
HTTPS-only cookies and redirects because the local Nginx endpoint is plain HTTP. It is not a
production profile.

```bash
cp .env.example .env
# Set DJANGO_SECRET_KEY, POSTGRES_PASSWORD, and the remaining values.
docker compose up --build
curl http://localhost:8080/health/
```

The backend container runs migrations and static-file collection before starting Gunicorn. This is
acceptable for a single local instance. Before horizontal scaling, move migrations to a controlled
release step.

Create the first platform administrator:

```bash
docker compose exec backend python manage.py create_platform_admin \
  --email platform@example.com \
  --full-name "Platform Administrator"
```

## Production requirements

Use `config.settings.production`. Startup fails unless:

- `DJANGO_SECRET_KEY` is set.
- `DB_ENGINE=postgresql` and database credentials are set.
- `REDIS_URL` is set.
- `DJANGO_ALLOWED_HOSTS` is set.

The application also needs:

- TLS termination at a trusted reverse proxy or load balancer.
- Forwarding headers set by that trusted proxy; clients must not be able to spoof them.
- `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` set to the deployed web origins.
- Secrets injected by the platform's secret manager, not baked into images.
- A release job running `python manage.py migrate --noinput`.
- `python manage.py collectstatic --noinput` with Nginx or an object store serving `/static/`.
- External PostgreSQL and Redis with persistence, backups, and monitoring.
- Gunicorn workers sized from measured load, not guessed. The current defaults are a starting point.

The included Nginx file is an HTTP development proxy. A production reverse proxy must terminate
TLS, redirect HTTP to HTTPS, set HSTS, and preserve the `X-Forwarded-*` headers expected by
`SECURE_PROXY_SSL_HEADER`.

## Monitoring

Application logs are JSON on stdout. Ship them to a centralized log system and alert on:

- 5xx rate and authentication failure spikes.
- Health-check failures.
- Database connection exhaustion and slow queries.
- Redis unavailability.
- Worker restarts and high request latency.

A dedicated error-monitoring service is not integrated yet.

## Capacity claim

No load test has been executed. Do not claim support for 500 concurrent students until a documented
test covers simultaneous login, exam start, answer saves, reconnection, and submission against the
production-like topology.
