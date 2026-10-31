# werkzeug-url-quote (skill)

**Verdict:** verified_repair

public tests and hidden evaluation checks passed

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: Werkzeug 3 removes werkzeug.urls.url_quote
- Failure class: import_error
- Repair source: skill:werkzeug-url-quote
- Attempts: 1
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 5.048
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
-werkzeug==2.3.8
+werkzeug==3.0.6
--- a/src/queryesc/encode.py
+++ b/src/queryesc/encode.py
@@ -1,5 +1,5 @@
-from werkzeug.urls import url_quote
+from urllib.parse import quote
 
 
 def encode_query_value(value: str) -> str:
-    return url_quote(value)
+    return quote(value, safe="/:!$'()*+,;")
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'import_error'}
- `propose` {'attempt': 1, 'source': 'skill:werkzeug-url-quote', 'abstain': False, 'model_call': False}
- `apply` {'attempt': 1, 'ok': True}
- `oracle` {'attempt': 1, 'ok': True}
