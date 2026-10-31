# Upgrade investigation procedure

This is the procedure the harness runs. The state names match the `timeline` in each evidence report. A proposer does not get to mark a run successful.

## Bounds

- One dependency, one target version.
- At most two repair attempts.
- At most two model calls, and only when the selected mode is `cpu` or `hosted`.
- A case stops at its timeout.
- A timed-out command may be retried once. The second timeout stops the case (`retry_limit`).
- Paid inference runs only in `hosted` mode with `UPGRADEPROOF_API_BASE`, `UPGRADEPROOF_API_KEY`, and `UPGRADEPROOF_MODEL` all set. There is no fallback from another mode into a paid call.

## States

1. **setup.** Create a virtualenv and install the project as it is pinned, plus pytest. The oracle directory is not copied into the workspace.
2. **baseline.** Run the project's public tests. If they fail, stop with `invalid_baseline`. Do not upgrade.
3. **upgrade.** Rewrite the single equality pin and reinstall from `requirements.txt`. If the resolver reports a conflict, stop with `constraint_conflict`.
4. **retest.** Run the public tests again.
   - If they pass, run the hidden oracle. Both green means `verified_bump` and the delivered patch is only the pin change. A public pass with an oracle failure is `unresolved`. Do not call it compatible.
5. **classify.** Map the failure log to one class: `unexpected_keyword`, `import_error`, `key_error`, `attribute_error`, `missing_argument`, `assertion_failure`, `syntax_error`, `type_error`, or `unknown`.
6. **propose.** Ask the selected proposer for a repair or an abstention.
   - `rules` may use a promoted rule whose package, failure class, and required error text all match, and whose old text is present in `src/`.
   - `skill` may use the same kind of match against `upgradeproof-repair` fences only. Prose in a skill is not a repair.
   - `cpu` and `hosted` must return JSON replacements or abstain. Their output is untrusted.
   - If nothing matches, abstain and stop with `unresolved`.
7. **reject or apply.** Reject a patch that edits tests, oracle files, or dependency metadata; that removes an `assert` line; that exceeds the file and line budget; or, for untrusted output, that touches a file outside the failure's call sites. A rejection consumes an attempt.
8. **retest the repair.** Run the public tests. On failure, one more attempt is allowed, with the new public failure as feedback. The oracle's assertions are not included in that feedback.
9. **oracle.** Run the hidden checks only after the public tests pass. If they fail, do not deliver the patch. Say `oracle_failed`.
10. **stop.** Either deliver `verified_repair` with the diff from the original project, or `unresolved` with the last reason and no delivered patch. Restore the unpatched upgraded tree when the result is not verified.

## Evidence

Every finished run records the verdict, the failure class, the repair source, attempt count, model calls, cost (zero unless a hosted price was configured), the commands' outcomes, and this limit:

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Promotion

A skill fence becomes a promoted rule only when a person passes `--accept` and the evidence verdict is `verified_repair` or `verified_bump`. The promoter copies the fence. It does not turn prose into a rule, and it does not re-run the tests.
