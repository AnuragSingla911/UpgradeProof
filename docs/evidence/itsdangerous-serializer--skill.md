# itsdangerous-serializer (skill)

**Verdict:** verified_repair

public tests and hidden evaluation checks passed

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with the new dependency in every environment.

## Run

- Title: itsdangerous 2 removes TimedJSONWebSignatureSerializer
- Failure class: import_error
- Repair source: skill:itsdangerous-timed-serializer
- Attempts: 1
- Model calls: 0
- Estimated cost (USD): 0.0000
- Wall clock, including shared setup (seconds): 4.135
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
-itsdangerous==1.1.0
+itsdangerous==2.2.0
--- a/src/tokens/issuer.py
+++ b/src/tokens/issuer.py
@@ -1,14 +1,11 @@
-from itsdangerous import TimedJSONWebSignatureSerializer
+from itsdangerous import URLSafeTimedSerializer
 
 
 def issue(payload: dict, secret: str) -> str:
-    serializer = TimedJSONWebSignatureSerializer(secret, expires_in=3600)
-    token = serializer.dumps(payload)
-    if isinstance(token, bytes):
-        return token.decode()
-    return token
+    serializer = URLSafeTimedSerializer(secret)
+    return serializer.dumps(payload)
 
 
 def read(token: str, secret: str) -> dict:
-    serializer = TimedJSONWebSignatureSerializer(secret, expires_in=3600)
-    return serializer.loads(token)
+    serializer = URLSafeTimedSerializer(secret)
+    return serializer.loads(token, max_age=3600)
```

## Timeline

- `baseline` {'ok': True, 'timed_out': False}
- `upgrade` {'ok': True, 'timed_out': False}
- `retest` {'ok': False, 'failure_class': 'import_error'}
- `propose` {'attempt': 1, 'source': 'skill:itsdangerous-timed-serializer', 'abstain': False, 'model_call': False}
- `apply` {'attempt': 1, 'ok': True}
- `oracle` {'attempt': 1, 'ok': True}
