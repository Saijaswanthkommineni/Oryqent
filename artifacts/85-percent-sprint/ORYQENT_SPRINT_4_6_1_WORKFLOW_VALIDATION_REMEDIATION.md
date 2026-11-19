# Oryqent Sprint 4.6.1: GitHub Actions Workflow Validation Remediation

- Repository: `C:\Users\saija\OneDrive\Desktop\Oryqent`
- Branch: `remediation/release-gates`
- Base commit: `9040a96f7bb11c98cbea21272457b7366e5218b5`
- Failing GitHub Actions run: `44551286923`
- Workflow file: `.github/workflows/ci.yml`

## 1. Root cause

GitHub rejected `ci.yml` at line 99, column 21 with `Unrecognized named-value: 'runner'. Expression: runner.temp`.

The `runner` context is only available in certain places in a workflow. It is valid in step-level `run`, `env`, `with`, and `if` blocks, but not in job-level `env` blocks. The backend-postgres job defined its shared evidence path at job level:

```yaml
jobs:
  backend-postgres:
    env:
      EVIDENCE_DIR: ${{ runner.temp }}/backend-postgres-evidence   # invalid here
```

## 2. Exact changes

Only `.github/workflows/ci.yml` was edited. No other files were changed.

1. Removed the job-level `EVIDENCE_DIR: ${{ runner.temp }}/...` entry from the `backend-postgres` job `env` block.
2. Rewrote the step `Create evidence directory` so that it resolves the path at runtime using the shell variable `$RUNNER_TEMP`, exports `EVIDENCE_DIR` to later steps through `$GITHUB_ENV`, and creates the directory:

```yaml
- name: Create evidence directory
  run: |
    echo "EVIDENCE_DIR=$RUNNER_TEMP/backend-postgres-evidence" >> "$GITHUB_ENV"
    mkdir -p "$RUNNER_TEMP/backend-postgres-evidence"
```

All later steps still reference `$EVIDENCE_DIR` in shell, so their behavior is unchanged.

`git diff --stat`: `ci.yml | 5 +++--` (3 insertions, 2 deletions).

## 3. Preserved behavior

- **Evidence logs:** Every step still writes to `$EVIDENCE_DIR`, which resolves to the same `$RUNNER_TEMP/backend-postgres-evidence` path as before. Log files 01 through 07 keep their names.
- **Artifact upload:** The `Upload backend evidence logs` step is unchanged. It still uses `${{ runner.temp }}/backend-postgres-evidence` in its `with.path`. That is a valid location for `runner.temp`, and it has `if: always()`, `retention-days: 14`, and `if-no-files-found: warn`.
- **PostgreSQL service:** The `postgres:17.12-alpine` service, its env, port mapping, and health options are unchanged.
- **Acceptance gate:** The 30 `apps.*` test IDs in the `PostgreSQL acceptance tests (exact 30, no skips allowed)` step are unchanged. The count was re-verified as 30. The `Found 30`, `Ran 30`, `skipped=`, and `OK` checks are unchanged.
- **Full suite:** The `Complete backend suite on PostgreSQL (no skips allowed)` step is unchanged.
- **Other jobs:** No other job was modified.

## 4. Validation evidence (local only)

1. **YAML parse:** `python -c "yaml.safe_load(...)"` on `.github/workflows/ci.yml` succeeded. Jobs found: `backend`, `backend-postgres`, `web`, `web-csp`, `mobile`, `android-runtime`, `infrastructure`.
2. **Embedded shell syntax:** All 35 `run:` blocks in `ci.yml` were extracted with `${{ ... }}` replaced by a placeholder, then checked with `bash -n` using Git Bash (`/usr/bin/bash`). Result: 0 failures.
   - The first attempt used the WSL-backed `bash` on PATH, which failed with `execvpe(/bin/bash) failed`. This was an environment problem, not a script problem. Git Bash was used for the final check.
3. **Context audit:** Every `${{ }}` expression in `ci.yml` was listed and checked against the contexts available at its location:
   - `env.PYTHON_VERSION`, `env.NODE_VERSION`, `env.FLUTTER_VERSION`: workflow-level env, used in step `with:`. Valid.
   - `github.ref`: used in `concurrency.group`. Valid.
   - `vars.ORYQENT_API_BASE_URL`: used in step-level `env`. Valid.
   - `secrets.*`: used in step-level `env`. Valid.
   - `runner.temp`: remaining use is in step `with.path` of the upload step. Valid. The invalid job-level use was removed.
   - No other invalid contexts were found. `runner.` no longer appears in any job-level `env` block.
4. **Acceptance gate count:** 30 `apps.*` test IDs remain in the gate step.
5. **Diff review:** `git diff -- .github/workflows/ci.yml` shows only the 5 intended lines changed.

Not run: `actionlint`, `act`, or any GitHub-hosted run. The repository does not include them, and they were not installed. The `ios-app.yml` workflow was not modified because the failure did not come from it. Its only expression, `vars.ORYQENT_API_BASE_URL`, is valid at step-level `env`.

## 5. Git safety

- No `git add .`, staging, commit, or push was performed.
- No remote, authentication, or credential settings were changed.
- Pre-existing working-tree changes were left untouched.

## 6. Verdict

**Local workflow validation: PASS.** The YAML parses, all embedded shell scripts pass `bash -n`, the invalid `runner.temp` job-level reference was removed, the other contexts are used at valid locations, and the 30-test gate and full-suite steps are preserved.

**Remote CI acceptance: NOT VERIFIED.** GitHub's own parser has not re-evaluated the file. The workflow has not run on GitHub, so the PostgreSQL acceptance gate, the full backend suite on PostgreSQL, the evidence upload, and every other job are unproven remotely. Remote acceptance requires pushing the branch with approval, then confirming a new run passes the workflow-validation step and the backend-postgres job.

## 7. Remaining limitations

- The fix addresses only the reported `runner.temp` error and the context audit. Other workflow errors could appear once GitHub gets further through validation, and this report cannot rule them out.
- `actionlint` was not run because it is not available in this environment. Running it locally would give a stronger schema check.
- The Git Bash `bash -n` check ignores `${{ }}` expressions by replacing them with a placeholder. This is correct for syntax but does not evaluate the values.
- The changes are uncommitted and unpushed, so GitHub has not seen them yet.
