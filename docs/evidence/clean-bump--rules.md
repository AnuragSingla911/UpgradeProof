# clean-bump (rules)

**Verdict:** verified_bump

the upgraded dependency passed public tests and hidden evaluation checks with no source change

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: The project already uses the urllib3 2 keyword
- Failure class: n/a
- Repair source: harness:version-bump
- Attempts: 0
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 4.428
- Baseline passed: yes
- Upgrade install passed: yes
- Public tests passed: yes
- Oracle passed: yes

## Patch rejections

- none

## Delivered patch

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@ -1 +1 @@
-urllib3==1.26.20
+urllib3==2.2.3
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': True, 'failure_class': None}
- `oracle` {'ok': True, 'bump': True}
