# Backup and restoration

No restoration has been executed yet. A restore drill is mandatory before production and after any
material schema change.

## Backup

Use PostgreSQL's custom format so restoration is selective and verifiable.

```bash
set -a
. ./.env
set +a
umask 077
docker compose exec -T db pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -Fc > "oryqent-$(date +%Y%m%dT%H%M%SZ).dump"
```

Store backups encrypted, off-host, with retention and access controls. Confirm every scheduled
backup has a nonzero size and a recorded checksum. Do not treat a successful `pg_dump` command as
proof that the backup is restorable.

## Restoration drill

Restore into a **new staging database**, never over production as a test:

```bash
docker compose exec -T db createdb -U "$POSTGRES_USER" oryqent_restore
docker compose exec -T db pg_restore \
  -U "$POSTGRES_USER" \
  -d oryqent_restore \
  --no-owner \
  --no-privileges < oryqent-YYYYMMDDTHHMMSSZ.dump
```

Then point a staging backend at `oryqent_restore`, run migrations, and verify:

1. `/health/` reports healthy.
2. Migration state matches the release.
3. User, institution, membership, and audit counts match expectations.
4. A known institution administrator can log in.
5. A known user cannot read another institution's records.
6. Audit records retain their actors and request IDs.

Record the elapsed restore time, any errors, and the verification result.

## Production recovery

Replacing a production database is destructive. It requires an authorized incident decision,
application downtime, and a final pre-restore backup. Do not run a restore over a live database.
After recovery, invalidate sessions/tokens if credential or authorization integrity is uncertain,
rotate exposed secrets, and review audit logs.
