# importlib-entry-points (rules)

**Verdict:** verified_repair

public tests and hidden evaluation checks passed

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: importlib_metadata 8 drops the entry_points() dict interface
- Failure class: key_error
- Repair source: rule:importlib-entry-points
- Attempts: 1
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 6.453
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
-importlib-metadata==4.13.0
+importlib-metadata==8.5.0
--- a/src/plugdemo/loader.py
+++ b/src/plugdemo/loader.py
@@ -2,5 +2,5 @@
 
 
 def plugin_names() -> list[str]:
-    selected = entry_points()["upgradeproof.plugins"]
+    selected = entry_points(group="upgradeproof.plugins")
     return sorted(entry.name for entry in selected)
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'key_error'}
- `propose` {'attempt': 1, 'source': 'rule:importlib-entry-points', 'abstain': False, 'model_call': False}
- `apply` {'attempt': 1, 'ok': True}
- `oracle` {'attempt': 1, 'ok': True}
