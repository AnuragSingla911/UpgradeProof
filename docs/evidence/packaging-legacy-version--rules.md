# packaging-legacy-version (rules)

**Verdict:** verified_repair

public tests and hidden evaluation checks passed

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: packaging 22 removes LegacyVersion
- Failure class: import_error
- Repair source: rule:packaging-legacy-version
- Attempts: 1
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 4.246
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
-packaging==21.3
+packaging==24.2
--- a/src/versions/describe.py
+++ b/src/versions/describe.py
@@ -1,8 +1,9 @@
-from packaging.version import LegacyVersion, parse
+from packaging.version import InvalidVersion, parse
 
 
 def describe(version: str) -> str:
-    parsed = parse(version)
-    if isinstance(parsed, LegacyVersion):
-        return f"legacy:{parsed}"
+    try:
+        parsed = parse(version)
+    except InvalidVersion:
+        return f"legacy:{version}"
     return f"pep440:{parsed}"
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'import_error'}
- `propose` {'attempt': 1, 'source': 'rule:packaging-legacy-version', 'abstain': False, 'model_call': False}
- `apply` {'attempt': 1, 'ok': True}
- `oracle` {'attempt': 1, 'ok': True}
