# Allowed changes and review standard

## Allowed

- The harness may change the one selected equality pin in `requirements.txt`.
- A repair may replace text in existing Python files under `src/`.
- A promoted rule or a skill fence may do that when its package, failure class, and error text match, and every `old` string is present.
- An untrusted model patch may do that only in files implicated by the traceback or by the symbol named in the error.
- The delivered patch for a verified repair is the pin change plus those source replacements. A verified bump is the pin change alone.

## Rejected before execution

- Any path outside `src/**/*.py`, including tests, oracle files, `requirements.txt`, and `pyproject.toml`.
- A replacement that removes a line that is an `assert` statement.
- An empty patch, a no-op replacement, or a patch over the file and line budget (5 files, about 80 lines).
- An untrusted edit to a file that is not part of this failure.

## Rejected after execution

- The public tests still fail.
- The public tests pass and the hidden oracle fails. The patch is not delivered. The model is not shown the oracle source or the oracle assertion text.
- The test command times out twice (`retry_limit`).

## Not a success

- `invalid_baseline`: the project failed before the upgrade.
- `constraint_conflict`: the requested version cannot be installed with the other requirements.
- `unresolved`: no repair was verified. This includes abstention, rejected patches, and exhausted attempts.

A green result is `verified_repair` or `verified_bump`. Both mean the public tests and the oracle passed on this machine for this fixture. Reviewers should still read the patch. The report's limitation line stays attached to the result.

## Where code runs

MCP file tools refuse paths that escape the workspace. That is an application check, not a sandbox. The project under test is ordinary code and can do what the process can do. GitHub Actions runs the suite in a job with `contents: read` and no secrets. Publishing a pull request, if it is added later, has to be a different job from the job that executes the case.
