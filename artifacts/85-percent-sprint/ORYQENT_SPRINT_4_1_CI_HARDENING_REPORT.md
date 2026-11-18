# ORYQENT Sprint 4.1: PostgreSQL CI Workflow Hardening Report

**Repository:** `C:\Users\saija\OneDrive\Desktop\Oryqent`
**Branch:** `remediation/release-gates` · **HEAD:** `5fc0a09` (`5fc0a09484cfe504ca245d7d75d41eb0b1586616`)
**Scope:** audit and harden `backend-postgres` in `.github/workflows/ci.yml`. No commit, push, remote CI trigger, Docker action, or Sprint 5 work.

## 1. Git state
- **Initial:** 38 modified tracked, 79 untracked, 0 staged.
- **Final:** 38 modified tracked, 79 untracked, 0 staged (unchanged). No staging, commits, stashes, resets, or deletions were performed.

## 2. Workflow tracking and triggers
- `.github/` is **untracked**, not ignored: `git ls-files .github` returns 0 files; `git check-ignore -v .github/workflows/ci.yml` returns no match (exit 1); `.gitignore` has no `.github` rule; `.git/info/exclude` contains only `/.freebuff/`.
- `HEAD` does not contain `.github/workflows/ci.yml`. Both `ci.yml` and `ios-app.yml` are untracked. The CI workflow therefore does not exist in the repository history yet.
- **Triggers** (`ci.yml`): `pull_request`; `push` on `main` and `remediation/**`; `workflow_dispatch`.
- **Before GitHub can run it:** the `.github/` directory must be committed on a branch that is pushed to the remote. The `backend-postgres` job runs only after that. This needs your approval; I have not staged or committed anything.

## 3. Issues found and corrected
| # | Issue | Correction |
|---|---|---|
| 1 | Steps that piped through `tee` (dependencies, migrate, makemigrations, ruff, system check) had no `set -o pipefail`. A failing command would be masked by `tee`'s exit status. | Added `set -o pipefail` to each of those five run blocks. |
| 2 | Acceptance step relied on `grep -q 'skipped='` and `^Ran 30 tests` / `^OK$` without checking discovery count or explicit failures. | Now asserts `^Found 30 test(s).$`, `^Ran 30 tests in .*$`, no `skipped=`, and an exact `OK` line. Each failure emits a `::error::` annotation and exits 1. |
| 3 | Full-suite step checked only skips and `OK`. | Keeps the no-skip rule and exact `OK` check, with an explicit error message. |
| 4 | Evidence directory was `backend/ci-logs`, inside the application tree. | Moved to `${{ runner.temp }}/backend-postgres-evidence` (env `EVIDENCE_DIR`), and the upload path matches. |
| 5 | Artifact name was generic. | Name `backend-postgres-evidence` is job-specific. Upload uses `if: always()`, `if-no-files-found: warn`, and `retention-days: 14`. |

## 4. Test-result format (validated against real Django output)
Sprint 3 log `artifacts/85-percent-sprint/sprint3-pg-logs/02-exact-30-tests.log` (CRLF stripped) contains:
- `Found 30 test(s).`
- `Ran 30 tests in 37.357s`
- `OK`

Each assertion in the workflow was run against that log locally: `Found 30 test(s).` matched, `Ran 30 tests in .*` matched, `skipped=` was absent, and `OK` matched. The full-suite log `10-full-suite-postgres-final.log` shows `Ran 525 tests` and `OK`, with no `skipped=` lines.

Note: Django's per-test verbose lines (`... ok`) are interleaved with migration output, so only 3 of 30 lines appear on a single line. The workflow therefore relies on summary lines, not per-test lines.

## 5. Exact test selection
- The acceptance step lists 30 method-level selectors, verified against `artifacts/85-percent-sprint/sprint3-pg-logs/exact-30-test-ids.txt`: 30 selectors, 30 unique, identical set (`match True`).
- Method-level selection means a missing or renamed test produces `Found` ≠ 30 and fails the step.
- The full suite is run after the focused acceptance step (step order is unchanged).

## 6. PostgreSQL job correctness (audit)
- Image pinned: `postgres:17.12-alpine`.
- Health check: `pg_isready -U oryqent_ci -d oryqent_ci` (5s interval, 20 retries) plus an explicit readiness loop step.
- Port bound `127.0.0.1:5432` only.
- Django env: `DB_ENGINE=postgresql`, `POSTGRES_DB/USER/PASSWORD=oryqent_ci`, `POSTGRES_HOST=127.0.0.1`, `POSTGRES_PORT=5432`, matching the `base.py` requirements (`DB_ENGINE == "postgresql"` requires DB name, user, password).
- Migrations run before tests (`migrate` step precedes acceptance and full suite).
- Settings: `config.settings.test` uses `setdefault`, so the job-level `DB_ENGINE` is honored. Inferred from code, not observed in a run.
- Skip risk: `skipUnlessDBFeature` tests skip silently on SQLite; on PostgreSQL the `skipped=` check and the count checks make a silent skip fail.
- Existing `backend` (SQLite) job: not modified by this sprint.

## 7. Credential handling
- Job credentials are CI-only placeholders: `ci-only-not-a-real-password` (service, `POSTGRES_PASSWORD`, `PGPASSWORD`) and `ci-only-not-a-real-secret-…` (`DJANGO_SECRET_KEY`). They are local to the ephemeral service container and do not grant access to any real system.
- No `secrets.*` references were added. Existing `secrets.ANDROID_*` references belong to the Android job, which is unchanged.
- No `echo`, `set -x`, or environment dumps in the new job. Logs contain Django/test output only.
- **Pre-existing, not changed:** the `backend` job's "Django deployment checks" step hardcodes a 64-character `DJANGO_SECRET_KEY` literal. It is used only for `check --deploy` in the SQLite job and is not a production credential, but it is a hardcoded value in the repo. Recommend moving it to a CI-only placeholder in a later sprint, not this one.

## 8. Log and artifact behavior
| Step | Log file | Exit behavior |
|---|---|---|
| Dependencies | `01-dependencies.log` | `pipefail`; failure fails job |
| Migrations | `02-migrate.log` | `pipefail`; failure fails job |
| makemigrations check | `03-makemigrations-check.log` | `pipefail`; failure fails job |
| Ruff | `04-ruff.log` | `pipefail`; failure fails job |
| System check | `05-system-check.log` | `pipefail`; failure fails job |
| Acceptance (30) | `06-postgres-acceptance.log` | fails on count ≠ 30, missing `Ran 30`, `skipped=`, or non-`OK` |
| Full suite | `07-full-suite-postgres.log` | fails on `skipped=` or non-`OK` |
| Upload | artifact `backend-postgres-evidence` | `if: always()`, 14-day retention |

Caveat: the acceptance and full-suite checks assert `OK`, which also fails on any failure or error (Django prints `FAILED (...)` instead). Per-test failure reasons are preserved in the log.

## 9. Local checks run (no Docker, no remote)
| Check | Command | Result |
|---|---|---|
| YAML parse | `yaml.safe_load(ci.yml)` | Parses; 7 jobs; `backend-postgres` has 12 steps; image `postgres:17.12-alpine` |
| Shell syntax | `bash -n` on the 9 extracted `run:` blocks | 9 checked, 0 failures |
| Selector resolution | compare workflow selectors to exact-30 file | 30 = 30, match True |
| Output-pattern validation | grep patterns against Sprint 3 log | Found 30 / Ran 30 / no skip / OK all matched |
| Upload path and retention | parsed YAML | path `${{ runner.temp }}/backend-postgres-evidence`, retention 14 |
| Ruff | `python -m ruff check .` | rc 0, "All checks passed!" (`sprint4-local-logs/41-ruff.log`) |
| Migration consistency | `makemigrations --check --dry-run` | rc 0, "No changes detected" (`42-makemigrations-check.log`) |
| System checks | `manage.py check --settings=config.settings.test` | rc 0, no issues (`43-system-check.log`) |

Earlier Sprint 4 logs `01-ruff.log`, `02-makemigrations-check.log`, `03-system-check.log` remain in the same folder.

## 10. Tests not executed
- The `backend-postgres` job was **not executed** (no PostgreSQL service locally; Docker unreachable and not started).
- The acceptance step's `grep` checks were validated against the Sprint 3 log, not a new run.
- Artifact upload was not executed; it runs only in GitHub Actions.
- The `runner.temp` path has not been resolved in a real runner.
- Full suite on PostgreSQL was not rerun in this sprint. Sprint 3 log `10-full-suite-postgres-final.log` (525 OK) remains the only evidence.

## 11. Remote CI prerequisites
1. Commit `.github/workflows/ci.yml` (and this report) on `remediation/release-gates`. The workflow is currently untracked.
2. Push the branch (requires approval).
3. Trigger the workflow via the `push` trigger or `workflow_dispatch`.
4. Confirm: `backend-postgres` passes; `Found 30 test(s).` and `Ran 30 tests` appear; no `skipped=`; full suite shows `Ran 525 tests` and `OK`; the artifact `backend-postgres-evidence` contains 7 logs.

## 12. Remaining blockers
- **Remote execution:** no GitHub run has occurred. PostgreSQL CI acceptance is not proven.
- **Untracked workflow:** `.github/` must be committed before GitHub sees it.
- **Hardcoded literal** in the existing `backend` job's deploy check (section 7).
- **Docker unreachable** locally, so the PostgreSQL acceptance cannot be reproduced on this machine.
- **Skip detection is textual**: the `skipped=` check depends on Django's summary format.

## 13. Completion
No new completion percentage is assigned. The Sprint 2 rubric and Sprint 3 reassessment (84.0% internal estimate) remain the baseline. No CI run has executed, so no score change is claimed.
