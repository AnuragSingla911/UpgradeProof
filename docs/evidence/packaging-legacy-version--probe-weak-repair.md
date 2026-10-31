# packaging-legacy-version (probe-weak-repair)

**Verdict:** unresolved

oracle_failed

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: packaging 22 removes LegacyVersion
- Failure class: import_error
- Repair source: n/a
- Attempts: 2
- Model calls: 2
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 4.656
- Baseline passed: yes
- Upgrade install passed: yes
- Public tests passed: yes
- Oracle passed: no

## Patch rejections

- none

## Delivered patch

```diff
(no delivered patch)
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'import_error'}
- `propose` {'attempt': 1, 'source': 'model:scripted', 'abstain': False, 'model_call': True}
- `apply` {'attempt': 1, 'ok': True}
- `oracle` {'attempt': 1, 'ok': False}
- `propose` {'attempt': 2, 'source': 'model:scripted', 'abstain': False, 'model_call': True}
- `apply` {'attempt': 2, 'ok': True}
- `oracle` {'attempt': 2, 'ok': False}
