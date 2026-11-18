# ORYQENT Sprint 4.2: Pre-Commit Workflow and Secret Review

**Repository:** `C:\Users\saija\OneDrive\Desktop\Oryqent` · **Branch:** `remediation/release-gates` · **HEAD:** `5fc0a09`
**Scope:** read-only audit. Nothing was staged, committed, pushed, reset, cleaned, stashed, or deleted. No containers were touched and no remote workflow was triggered.

## 1. Findings: workflow files

| Item | `ci.yml` ("Release gates") | `ios-app.yml` ("iOS (unsigned archive)") |
|---|---|---|
| Exists in HEAD | No (`git ls-files .github` = 0; HEAD has no `.github` paths) | No (not in HEAD) |
| Existed before Sprint 4 | Created in Sprint 4 (added `backend-postgres`; the rest of the file is pre-existing content in an untracked file) | Pre-existing on disk (mtime 2026-11-11, before Sprint 4); never tracked |
| Triggers | `pull_request`; `push` on `main` and `remediation/**`; `workflow_dispatch` | `workflow_dispatch`; `pull_request` and `push` (branch `main`) filtered to `apps/mobile/**` and its own file |
| Jobs | `backend`, `backend-postgres`, `web`, `web-csp`, `mobile`, `android-runtime`, `infrastructure` | `ios-unsigned-build` (macOS 15) |
| External actions | `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`, `actions/setup-java@v4`, `actions/upload-artifact@v4`, `subosito/flutter-action@v2`, `reactivecircus/android-emulator-runner@v2` | `actions/checkout@v4`, `subosito/flutter-action@v2`, `actions/upload-artifact@v4` |
| Secrets | `secrets.ANDROID_KEYSTORE_PASSWORD`, `secrets.ANDROID_KEY_PASSWORD` (references only, no literal values). Hardcoded: a `DJANGO_SECRET_KEY` literal in the `backend` job and CI-only placeholder passwords in `backend-postgres` | No secrets. Uses `vars.ORYQENT_API_BASE_URL` with a non-secret `.invalid` default |
| Safe to track | `ci.yml`: yes, after the deploy-check literal is replaced (section 2) | `ios-app.yml`: safe (no credentials), but it is not part of Sprint 4 and should be committed only if you want it |

**Note on `ios-app.yml`:** it predates Sprint 4 as an untracked file. Its history is outside this sprint, so it should not be bundled into the Sprint 4 commit.

## 2. Secret handling

| Occurrence | Location | Assessment |
|---|---|---|
| `DJANGO_SECRET_KEY: [REDACTED]` | `ci.yml` line 51, `backend` job, "Django deployment checks" | **Not safe as written.** The literal looks like a generated, real-format key and is hardcoded in version control. It is not present in any tracked file (HEAD), so it is not yet committed. It is used only for `check --deploy`, so it is not a production credential, but it should not be committed. Replace it before committing. |
| `ci-only-not-a-real-secret-…` | `ci.yml` line 92, `backend-postgres` env | Disposable by design: the name states it is CI-only and the value is a placeholder, not a usable key. |
| `ci-only-not-a-real-password` | `ci.yml` lines 59, 74, 89, 119 | Disposable: used only by the throwaway PostgreSQL service container. Its role and database exist only for the job. |
| `secrets.ANDROID_*` | `ci.yml` lines 322, 324 | Correct use of the repository secrets mechanism. |

**Recommended CI-only replacement for the deploy-check key:** a clearly fake placeholder that is long enough to pass Django's check, such as `ci-only-deploy-check-secret-key-not-for-production-0123456789abcdef`, or generated at runtime with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. This is a `ci.yml` change only. No production settings or real credentials are involved.

## 3. Sprint 4 PostgreSQL job audit (`backend-postgres`)

| Check | Result |
|---|---|
| `pipefail` coverage | 8 `set -o pipefail` lines in the job: all 7 `tee` run blocks (dependencies, migrate, makemigrations, ruff, system check, acceptance, full suite) plus the readiness step. |
| PostgreSQL service | Image `postgres:17.12-alpine` (pinned). `pg_isready -U oryqent_ci -d oryqent_ci` health check, 5s interval, 20 retries. Port bound `127.0.0.1:5432`. Explicit readiness loop step also present. |
| Django env vs settings | `DB_ENGINE=postgresql`, `POSTGRES_DB/USER/PASSWORD=oryqent_ci`, `POSTGRES_HOST=127.0.0.1`, `POSTGRES_PORT=5432`. `base.py` requires NAME, USER and PASSWORD when `DB_ENGINE=postgresql`, so all three are set. |
| Exact 30 selection | 30 method-level selectors, 30 unique, identical to `sprint3-pg-logs/exact-30-test-ids.txt` (verified in Sprint 4.1). |
| Acceptance failure paths | Fails on `Found` != 30 (`^Found 30 test(s).$` required), missing `Ran 30 tests in`, any `skipped=`, or no exact `OK` line. Failing tests produce `FAILED (...)`, so the `OK` check also fails on failures and errors. |
| Full-suite skip handling | Fails on any `skipped=` and requires exact `OK`. No documented skip exemption exists in the repo, so zero skips is the intended behavior. |
| Artifact upload | `if: always()`, so it runs after failed steps. `if-no-files-found: warn`. |
| Retention | `retention-days: 14`. |
| Log credentials | No `echo` of env variables, no `set -x`. Logs contain Django and tool output only. The database password is passed in the service env and `PGPASSWORD`, so it is not printed. |
| SQLite `backend` job | Unchanged in Sprint 4 (its only literal change would be the deploy-check key, which is recommended below). |

### Remaining weaknesses (not proven by local checks)
1. **Runtime is unproven.** Nothing here shows the job passes on GitHub. The `runner.temp` path and artifact upload only run remotely.
2. **Textual skip detection.** The `skipped=` and `OK` checks depend on Django's summary format. They are verified against the Sprint 3 log, not against a new run.
3. **Unverified `DB_ENGINE` override.** `config.settings.test` uses `setdefault`, so the job's `DB_ENGINE=postgresql` is honored by inference from code, not observed.
4. **Untracked workflow.** `.github/` is not in HEAD, so no commit or push can run it until it is committed.

## 4. Git scope

- **Current status:** 38 modified tracked, 79 untracked, 0 staged. `artifacts/85-percent-sprint/` is entirely untracked (`?? artifacts/85-percent-sprint/`).
- **`.github/`:** untracked, not ignored (`git check-ignore` returns no match; `.gitignore` has no `.github` rule; `.git/info/exclude` only has `/.freebuff/`). `git ls-files .github` = 0.
- **Unrelated pre-existing changes (leave untouched):** the 38 modified tracked files, including `backend/config/settings/base.py` (144 insertions, 2 deletions against HEAD) and the other `backend/` changes (27 files, 1008 insertions, 80 deletions). None were modified by Sprint 4. The 79 untracked entries include the other sprint artifacts and the unrelated app code.
- **Minimal Sprint 4 commit scope:**
  1. `.github/workflows/ci.yml` (after the deploy-check literal is replaced)
  2. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_POSTGRESQL_CI_AND_EVIDENCE_REPORT.md`
  3. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_1_CI_HARDENING_REPORT.md`
  4. `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_2_PRECOMMIT_REVIEW.md`
  5. `artifacts/85-percent-sprint/sprint3-pg-logs/exact-30-test-ids.txt` and the Sprint 3 logs it references, only if those evidence files are meant to be versioned.
  6. `artifacts/85-percent-sprint/sprint4-local-logs/` (optional; local check output).
- **Exclude:** `ios-app.yml`, all `backend/` settings changes, `apps/mobile/` files, and every other untracked or modified file.
- **Independent commit:** yes. `ci.yml` does not reference `ios-app.yml`, so the workflow can be committed alone. `ios-app.yml` should be a separate commit or left out.

## 5. Local checks performed (Sprint 4.2)

| Check | Result |
|---|---|
| Inspect `ci.yml` and `ios-app.yml` triggers, jobs, actions, secrets | Done (sections 1 and 2) |
| `git status`, `git ls-files .github`, `git check-ignore`, `git ls-tree HEAD` | Done (section 4) |
| Literal scan of tracked HEAD for the deploy-check key | 0 matches in HEAD; 1 match in the untracked `ci.yml` |
| Pipefail / tee / selector audit of `backend-postgres` | Done (section 3) |

No tests were run in this sprint. The Sprint 4.1 local checks (YAML, shell syntax, selectors, ruff, migration check, system check) remain valid because no workflow or backend file changed in Sprint 4.2.

## 6. Remote checks still pending
- No GitHub Actions run. `backend-postgres` and the artifact upload are unproven.
- The `backend` job's deploy check has not been run with the replacement key.
- No PostgreSQL acceptance run in CI; the Sprint 3 logs are the only PostgreSQL evidence.

## 7. Statement

**Nothing was staged, committed, or pushed.** No remote workflow was triggered. No Docker or container changes were made. No files were deleted, reset, cleaned, or stashed. The only file created in this sprint is this report.

## 8. Recommended action before commit
1. Replace the `backend` job's deploy-check `DJANGO_SECRET_KEY` literal with a CI-only placeholder (section 2).
2. Commit only the minimal scope in section 4 after your approval.
3. Push only after your approval, then verify the first `backend-postgres` run.
