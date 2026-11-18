# ORYQENT Sprint 4.3: Final Commit Scope

**Repository:** `C:\Users\saija\OneDrive\Desktop\Oryqent` · **Branch:** `remediation/release-gates` · **HEAD:** `5fc0a09`

## 1. Secret remediation

**Change made:** in `.github/workflows/ci.yml`, the `backend` job's hardcoded `DJANGO_SECRET_KEY` literal was removed. A new step, "Generate disposable deploy-check secret", now generates the value at runtime:

- `secrets.token_urlsafe(64)` produces about 86 characters, which passes the production validator (at least 50 characters, at least 5 distinct characters, no `django-insecure-` prefix, no `replace-with`, `change-me`, or `changeme` substring).
- The value is passed through `::add-mask::` so the runner redacts it from logs.
- It is written only to `$GITHUB_ENV`, which is job-scoped and not persisted to artifacts.
- The "Django deployment checks" step's other env values are unchanged.

**Why this is safe:** the value is generated fresh on each run, is never printed, and is never stored in the repository or in any artifact. It is not a production or developer secret.

**Not changed:** `config/settings/production.py`, `base.py`, and every other settings file.

## 2. Verification (local)

| Check | Result |
|---|---|
| `ci.yml` parses as YAML | Pass; 7 jobs: `backend`, `backend-postgres`, `web`, `web-csp`, `mobile`, `android-runtime`, `infrastructure` |
| Shell syntax (`bash -n`) of all 15 `run` blocks in `backend` and `backend-postgres` | Pass, 0 failures (run via `/usr/bin/bash`) |
| Hardcoded `DJANGO_SECRET_KEY` literal removed | Pass: `Zk8vQ2mN7pR4` no longer appears in `ci.yml` |
| Remaining CI-only placeholder | Line 97 only (`backend-postgres` env); a disposable placeholder, not a usable secret |
| PostgreSQL service | Pass: `postgres:17.12-alpine`, `pg_isready` health check (5s interval, 5s timeout, 20 retries), `127.0.0.1:5432` |
| Exact 30 test IDs | Pass: 30 selectors in `ci.yml`, 30 unique, identical set to `sprint3-pg-logs/exact-30-test-ids.txt` |
| Acceptance log checks | Present: `Found 30 test(s).`, `Ran 30 tests in`, no `skipped=`, exact `OK` |
| Artifact upload | Pass: `actions/upload-artifact@v4`, `name: backend-postgres-evidence`, path `${{ runner.temp }}/backend-postgres-evidence`, `if-no-files-found: warn`, `retention-days: 14`, `if: always()` |
| SQLite `backend` job | Unchanged except the secret correction (Django deployment checks step now uses the generated key) |

**Limitations:** the `Generate` step and the deploy check were not executed. The YAML and shell checks are static. Local Python subprocess calls to `bash` failed (WSL relay); the syntax check was run through `/usr/bin/bash` instead.

## 3. Proposed Sprint 4 commit scope

**Include (exact files):**
1. `.github/workflows/ci.yml`: the workflow with the `backend-postgres` job and the secret remediation.
2. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_POSTGRESQL_CI_AND_EVIDENCE_REPORT.md`
3. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_1_CI_HARDENING_REPORT.md`
4. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_2_PRECOMMIT_REVIEW.md`
5. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_3_FINAL_COMMIT_SCOPE.md`
6. Optional, only if versioning evidence is wanted: `artifacts/85-percent-sprint/sprint3-pg-logs/exact-30-test-ids.txt` and `artifacts/85-percent-sprint/sprint3-pg-logs/02-exact-30-tests.log`
7. Optional: `artifacts/85-percent-sprint/sprint4-local-logs/` (local check output)

**Exclude (deliberately):**
- `.github/workflows/ios-app.yml`: untracked, pre-Sprint 4, independent of `ci.yml`. Commit separately or leave out.
- All 38 modified tracked files, including `backend/config/settings/base.py` (144 insertions), `backend/` changes, and `apps/mobile/` changes. None belong to Sprint 4.
- All other untracked entries, including unrelated app and mobile files.

**Preserve (do not modify, stage, or delete):** all 38 modified tracked files and all untracked entries not listed above. Nothing was reset, cleaned, or stashed.

**Can the workflow be committed without `ios-app.yml`?** Yes. `ci.yml` has no reference to `ios-app.yml` and no dependency on it.

## 4. Current Git state (read-only)

- Staged files: 0.
- Modified tracked: 38. Untracked: 79 plus `.github/` and `artifacts/85-percent-sprint/` directories.
- `git status --porcelain | wc -l` = 117.
- `.github/` is untracked, not ignored. `artifacts/85-percent-sprint/` is untracked.

## 5. Remote CI still pending

- No GitHub Actions run has been executed for `backend-postgres` or the deploy check.
- The artifact upload and `runner.temp` resolution are unproven.
- The generated deploy-check secret has not been run through `manage.py check --deploy` in CI.
- The PostgreSQL acceptance tests have not run in CI; the Sprint 3 logs are the only PostgreSQL evidence.

## 6. Confirmation

**Nothing was staged, committed, or pushed.** No remote workflow was triggered. No Docker or container changes were made. Nothing was reset, cleaned, stashed, or deleted. The only file changes in this sprint are the `ci.yml` secret remediation and this report.
