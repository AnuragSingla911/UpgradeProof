# urllib3-retry (rules)

**Verdict:** verified_repair

public tests and hidden evaluation checks passed

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: urllib3 2 removes Retry(method_whitelist=...)
- Failure class: unexpected_keyword
- Repair source: rule:urllib3-retry-method-whitelist
- Attempts: 1
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 5.032
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
--- a/src/retryctx/client.py
+++ b/src/retryctx/client.py
@@ -2,4 +2,4 @@
 
 
 def build_retry() -> Retry:
-    return Retry(total=3, method_whitelist=["GET", "HEAD"], status_forcelist=[503])
+    return Retry(total=3, allowed_methods=["GET", "HEAD"], status_forcelist=[503])
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'unexpected_keyword'}
- `propose` {'attempt': 1, 'source': 'rule:urllib3-retry-method-whitelist', 'abstain': False, 'model_call': False}
- `apply` {'attempt': 1, 'ok': True}
- `oracle` {'attempt': 1, 'ok': True}
