# markupsafe-soft-unicode (rules)

**Verdict:** unresolved

no promoted repair matches this failure

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: MarkupSafe 2.1 removes soft_unicode; no promoted rule
- Failure class: import_error
- Repair source: rule
- Attempts: 1
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 3.747
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
- `retest` {'ok': False, 'failure_class': 'import_error'}
- `propose` {'attempt': 1, 'source': 'rule', 'abstain': True, 'model_call': False}
