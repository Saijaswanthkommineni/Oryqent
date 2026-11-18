# ORYQENT Sprint 4: PostgreSQL CI Integration and Evidence Report

**Branch:** `remediation/release-gates` · **Initial HEAD:** `5fc0a09484cfe504ca245d7d75d41eb0b1586616`
**Initial Git state:** 38 modified tracked, 79 untracked, 0 staged.
**Final Git state:** 38 modified tracked, 79 untracked, 0 staged (unchanged count; `.github/` is one untracked entry, and this report is also among the untracked entries). No commits, stashes, resets, or pushes.

## 1. CI architecture discovered
- GitHub Actions. Workflow `.github/workflows/ci.yml` ("Release gates"), plus `ios-app.yml`.
- Existing `backend` job (ubuntu-latest): ruff, `makemigrations --check`, full suite on `config.settings.test` (SQLite in-memory), and `check --deploy` with placeholder PostgreSQL env vars. It does not start PostgreSQL.
- `config.settings.test` forces `DB_ENGINE=sqlite` through `setdefault`. `base.py` uses PostgreSQL only when `DB_ENGINE=postgresql`.
- PostgreSQL-only tests use `@skipUnlessDBFeature("has_select_for_update")`, so they skip silently on SQLite.
- Log retention before this sprint: none for backend jobs. Only the web-csp Playwright report was uploaded.

## 2. Files changed
| File | Change | Reason |
| --- | --- | --- |
| `.github/workflows/ci.yml` | Added new job `backend-postgres` (after `backend`). Existing jobs untouched. | Run the Sprint 3 exact-30 PostgreSQL acceptance and full PostgreSQL suite in CI, with retained logs and skip checks. |
| `artifacts/85-percent-sprint/ORYQENT_SPRINT_4_POSTGRESQL_CI_AND_EVIDENCE_REPORT.md` | New report | This document. |

No application code, settings, or tests were modified. The SQLite `backend` job is unchanged.

**Note:** `.github/` is untracked in this repository, so `git diff` cannot show the workflow change. The full file content is the authoritative state.

## 3. PostgreSQL service configuration (`backend-postgres`)
- Image: `postgres:17.12-alpine` (pinned; same version as Sprint 3 evidence).
- Database `oryqent_ci`, user `oryqent_ci`, password `ci-only-not-a-real-password` (CI-only placeholder, not a production credential).
- Port bound to `127.0.0.1:5432`, reachable only inside the job.
- Health check: `pg_isready` with 5s interval, 20 retries; the job also runs an explicit readiness loop step.
- Job env: `DB_ENGINE=postgresql`, `POSTGRES_HOST=127.0.0.1`, `POSTGRES_PORT=5432`, `DJANGO_SECRET_KEY` (CI-only), `DJANGO_DEBUG=false`.
- Django test settings still use `config.settings.test`. Because `setdefault` keeps `DB_ENGINE=postgresql`, the test run uses PostgreSQL. Migrations apply through the same settings.

## 4. Job steps and per-stage logs (retained in `backend/ci-logs`)
| Step | Log | Failure behavior |
| --- | --- | --- |
| PostgreSQL readiness (pg_isready loop) | step output | exit 1 after 30 tries |
| Install dependencies | `01-dependencies.log` | pip failure fails job |
| Apply migrations | `02-migrate.log` | migrate failure fails job |
| Migration consistency check | `03-makemigrations-check.log` | non-zero exit fails job |
| Ruff | `04-ruff.log` | non-zero exit fails job |
| Django system checks | `05-system-check.log` | non-zero exit fails job |
| PostgreSQL acceptance (exact 30) | `06-postgres-acceptance.log` | fails if `skipped=` appears, or if `Ran 30 tests` / `OK` is absent |
| Complete backend suite on PostgreSQL | `07-full-suite-postgres.log` | fails if `skipped=` appears, or if `OK` is absent |
| Upload evidence | artifact `backend-postgres-evidence` (14 days) | `if: always()` |

The acceptance step runs the exact 30 method IDs from `artifacts/85-percent-sprint/sprint3-pg-logs/exact-30-test-ids.txt`. I verified that the 30 selectors in the workflow match that file exactly (30 unique, identical set).

## 5. Commands and actual results (local, non-infrastructure)
| Check | Command | Result |
| --- | --- | --- |
| YAML parse | `yaml.safe_load` on `ci.yml` | Parses; 7 jobs including `backend-postgres`; PostgreSQL image `postgres:17.12-alpine`; 12 steps |
| Shell syntax | `bash -n` on all 9 extracted `run:` scripts | All 9 pass |
| Selection check | Compare workflow selectors to exact-30 file | 30 = 30, match True |
| Test discovery | Django `TestLoader` on the 12 classes | 46 tests loaded from classes (the exact 30 are a subset; the job selects methods) |
| Ruff | `python -m ruff check .` | rc 0, "All checks passed!" (`artifacts/85-percent-sprint/sprint4-local-logs/01-ruff.log`) |
| Migration consistency | `makemigrations --check --dry-run` | rc 0, "No changes detected" (`02-makemigrations-check.log`) |
| System check | `manage.py check --settings=config.settings.test` | rc 0, no issues (`03-system-check.log`) |

## 6. Not run (and why)
- **The PostgreSQL acceptance job and full PostgreSQL suite were not run in this sprint.** Running them locally needs Docker Desktop, which is unreachable from this shell (`npipe` missing), and I did not start Docker or change containers. Sprint 3 logs remain the only PostgreSQL evidence.
- **Remote GitHub Actions was not triggered.** No push, no workflow dispatch, and no external infrastructure, per instruction.
- YAML validation used a local PyYAML install in `backend/.venv` (not part of the project requirements).

## 7. Remaining CI limitations
1. **Unverified in CI:** the new job has not executed on GitHub. Until a remote run completes, PostgreSQL CI acceptance is **not proven**.
2. **Placeholder secrets:** the `ci-only-*` password and secret are intentional CI-only values, but they are visible in the workflow file.
3. **`.github/` untracked:** the workflow must be committed before any remote run can use it.
4. **Skip detection is textual:** the job fails when `skipped=` appears in the log. A skipped test that prints nothing would pass the check, so the `Ran 30`/`OK` assertions are the primary control.
5. **Full PostgreSQL suite not in the same job as deploy checks:** `check --deploy` still uses the existing `backend` job's placeholders.
6. **No artifact check after upload:** the upload step does not verify contents.

## 8. Remote CI execution
**Pending.** The workflow is configured but has not been pushed or triggered. Remote execution requires your approval to push the branch.

## 9. Is the Sprint 3 acceptance reproducible?
**Partially, and not yet demonstrated in CI.** The exact 30 IDs, the PostgreSQL 17.12 image, and the settings path are now wired into the workflow. The selection matches Sprint 3. Reproduction is shown by the Sprint 3 logs, not by any CI run. The Sprint 3 full-suite 525/525 result is also not reproduced here.

## 10. Completion
No new completion percentage is assigned. The Sprint 2 rubric and the Sprint 3 reassessment (84.0% internal estimate) remain the baseline. Since no CI run has executed, no score increase is claimed.

## 11. Next step (requires approval)
Commit the workflow and this report on the branch, push, and inspect the first `backend-postgres` run. Confirm the job passes, the 30 tests run (no skips), the 525-test suite passes, and the `backend-postgres-evidence` artifact contains all 7 logs.
