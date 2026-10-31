# constraint-conflict (rules)

**Verdict:** constraint_conflict

dependency resolver rejected the requested version

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: Another local requirement forbids urllib3 2
- Failure class: constraint_conflict
- Repair source: n/a
- Attempts: 0
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 6.526
- Baseline passed: yes
- Upgrade install passed: no
- Public tests passed: not run
- Oracle passed: not run

## Patch rejections

- none

## Delivered patch

```diff
(no delivered patch)
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': False, 'timed_out': False}
