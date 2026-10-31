# itsdangerous timed serializer

## When this applies

itsdangerous 2.0 removed `TimedJSONWebSignatureSerializer`. Code that imported it on 1.1 fails immediately:

`ImportError: cannot import name 'TimedJSONWebSignatureSerializer'`

The 1.1 helper also took `expires_in` on the constructor and `dumps` returned `bytes`. `URLSafeTimedSerializer` returns `str` and takes the lifetime as `max_age` on `loads`.

Tokens are not compatible across the two classes. This repair preserves "issue a payload, read it back, reject a tampered token" for tokens created after the upgrade. It does not read tokens that were signed by the removed class.

## Migration

```python
from itsdangerous import URLSafeTimedSerializer

def issue(payload: dict, secret: str) -> str:
    serializer = URLSafeTimedSerializer(secret)
    return serializer.dumps(payload)

def read(token: str, secret: str) -> dict:
    serializer = URLSafeTimedSerializer(secret)
    return serializer.loads(token, max_age=3600)
```

## Executable fence

```upgradeproof-repair
id = "itsdangerous-timed-serializer"
package = "itsdangerous"
error_class = "import_error"
error_contains = ["TimedJSONWebSignatureSerializer"]

[[replacements]]
path_glob = "src/**/*.py"
old = '''from itsdangerous import TimedJSONWebSignatureSerializer'''
new = '''from itsdangerous import URLSafeTimedSerializer'''

[[replacements]]
path_glob = "src/**/*.py"
old = '''    serializer = TimedJSONWebSignatureSerializer(secret, expires_in=3600)
    token = serializer.dumps(payload)
    if isinstance(token, bytes):
        return token.decode()
    return token'''
new = '''    serializer = URLSafeTimedSerializer(secret)
    return serializer.dumps(payload)'''

[[replacements]]
path_glob = "src/**/*.py"
old = '''    serializer = TimedJSONWebSignatureSerializer(secret, expires_in=3600)
    return serializer.loads(token)'''
new = '''    serializer = URLSafeTimedSerializer(secret)
    return serializer.loads(token, max_age=3600)'''
```

## What a passing test does not mean

A round trip of one dict does not prove expiry, key rotation, or compatibility with tokens already stored in a database.
