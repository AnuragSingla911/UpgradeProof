# UpgradeProof feasibility results

Generated 2026-10-31 13:42 Asia/Calcutta. Elapsed 54.356s.

These fixtures were written for this repository. Promoted rules were authored with the cases, so the repair rate is a feasibility result, not an estimate for unseen upgrades. A passing oracle is not universal compatibility.

## Cases

Row times each include that case's environment setup. Two modes share the setup, so those times are not additive. `elapsed_seconds` is the wall clock for the whole command.

| Case | Cohort | Mode | Verdict | Model calls | Seconds | Expectation |
|---|---|---|---|---:|---:|---|
| urllib3-retry | repair | rules | verified_repair | 0 | 5.032 | met |
| urllib3-retry | repair | skill | verified_repair | 0 | 5.029 | met |
| werkzeug-url-quote | repair | rules | verified_repair | 0 | 5.108 | met |
| werkzeug-url-quote | repair | skill | verified_repair | 0 | 5.048 | met |
| importlib-entry-points | repair | rules | verified_repair | 0 | 6.453 | met |
| importlib-entry-points | repair | skill | verified_repair | 0 | 6.534 | met |
| itsdangerous-serializer | repair | rules | verified_repair | 0 | 4.108 | met |
| itsdangerous-serializer | repair | skill | verified_repair | 0 | 4.135 | met |
| packaging-legacy-version | repair | rules | verified_repair | 0 | 4.246 | met |
| packaging-legacy-version | repair | skill | verified_repair | 0 | 4.244 | met |
| markupsafe-soft-unicode | uncovered | rules | unresolved | 0 | 3.747 | met |
| markupsafe-soft-unicode | uncovered | skill | unresolved | 0 | 3.756 | met |
| invalid-baseline | adversarial | rules | invalid_baseline | 0 | 3.154 | met |
| clean-bump | adversarial | rules | verified_bump | 0 | 4.428 | met |
| constraint-conflict | adversarial | rules | constraint_conflict | 0 | 6.526 | met |

## Metrics

- **repair/rules**: 5/5 expectations met, 5/5 verified verdicts, 0 delivered regressions, 0 model calls, cost/verified USD 0.0
- **repair/skill**: 5/5 expectations met, 5/5 verified verdicts, 0 delivered regressions, 0 model calls, cost/verified USD 0.0
- **uncovered/rules**: 1/1 expectations met, 0/1 verified verdicts, 0 delivered regressions, 0 model calls, cost/verified USD None
- **uncovered/skill**: 1/1 expectations met, 0/1 verified verdicts, 0 delivered regressions, 0 model calls, cost/verified USD None
- **adversarial/rules**: 3/3 expectations met, 1/3 verified verdicts, 0 delivered regressions, 0 model calls, cost/verified USD 0.0

## Execution probes

- pass: invented urllib3 keyword is caught by execution → unresolved (tests_still_failing)
- pass: packaging repair that passes public tests but fails the oracle is not delivered → unresolved (oracle_failed)

## Guard checks

- pass: invalid_baseline → invalid_baseline
- pass: constraint_conflict → constraint_conflict
- pass: verified_bump → verified_bump
- pass: reject_protected_test_edit → unresolved
- pass: reject_unrelated_edit → unresolved
- pass: reject_deleted_assert → unresolved
- pass: invented_api_caught_by_execution → unresolved
- pass: oracle_failure_not_delivered → unresolved
- pass: retry_limit → unresolved
- pass: abstain → unresolved

## Promotion

- First encounter: model:scripted-first-encounter verified=True model_calls=1
- Maintainer accepted: True
- Later encounter: rule:urllib3-retry-method-whitelist verified=True model_calls=0

## CPU model

- Status: unavailable: set UPGRADEPROOF_GGUF to a local GGUF file
