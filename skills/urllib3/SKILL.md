# urllib3 Retry `method_whitelist`

## When this applies

urllib3 2.0 removed the `Retry` keyword `method_whitelist`. Releases in the 1.26 line accept it and warn. A project pinned below 2.0 fails on 2.x with:

`TypeError: Retry.__init__() got an unexpected keyword argument 'method_whitelist'`

## Migration

Callers pass the methods that are safe to retry:

```python
Retry(total=3, method_whitelist=["GET", "HEAD"])
```

becomes:

```python
Retry(total=3, allowed_methods=["GET", "HEAD"])
```

Leave `total`, `status_forcelist`, and the method list as they are. Renaming the keyword is the whole repair for this break.

## Executable fence

Skill mode runs only the fence below. The prose and the Python samples are not executed. Promoting this fence into `rules/promoted/` is a separate maintainer action after a verified run.

```upgradeproof-repair
id = "urllib3-retry-method-whitelist"
package = "urllib3"
error_class = "unexpected_keyword"
error_contains = ["method_whitelist"]

[[replacements]]
path_glob = "src/**/*.py"
old = '''method_whitelist='''
new = '''allowed_methods='''
```

## What a passing test does not mean

A green public suite shows that the renamed keyword still builds a retry policy the tests inspect. It does not show that every HTTP call site in a larger program retries the same way.
