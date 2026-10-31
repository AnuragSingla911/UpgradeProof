# urllib3-retry (probe-invented-api)

**Verdict:** unresolved

tests_still_failing

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: urllib3 2 removes Retry(method_whitelist=...)
- Failure class: unexpected_keyword
- Repair source: n/a
- Attempts: 2
- Model calls: 2
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 5.305
- Baseline passed: yes
- Upgrade install passed: yes
- Public tests passed: no
- Oracle passed: not run

## Patch rejections

- none

## Delivered patch

```diff
(no delivered patch)
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'unexpected_keyword'}
- `propose` {'attempt': 1, 'source': 'model:scripted', 'abstain': False, 'model_call': True}
- `apply` {'attempt': 1, 'ok': True}
- `retest_repair` {'attempt': 1, 'ok': False, 'failure_class': 'unexpected_keyword'}
- `propose` {'attempt': 2, 'source': 'model:scripted', 'abstain': False, 'model_call': True}
- `apply` {'attempt': 2, 'ok': True}
- `retest_repair` {'attempt': 2, 'ok': False, 'failure_class': 'unexpected_keyword'}
