# importlib.metadata entry point groups

## When this applies

`importlib_metadata` 4.x returns a dict-like object from `entry_points()`, so `entry_points()["group"]` selects a group. That interface is gone by 8.x. The same call raises `KeyError` because indexing no longer means "select this group".

The supported call on both 4.13 and 8.x is `entry_points(group="...")`.

## Migration

```python
selected = entry_points()["upgradeproof.plugins"]
```

becomes:

```python
selected = entry_points(group="upgradeproof.plugins")
```

## Executable fence

```upgradeproof-repair
id = "importlib-entry-points"
package = "importlib_metadata"
error_class = "key_error"
error_contains = ["upgradeproof.plugins"]

[[replacements]]
path_glob = "src/**/*.py"
old = '''entry_points()["upgradeproof.plugins"]'''
new = '''entry_points(group="upgradeproof.plugins")'''
```

## What a passing test does not mean

Listing entry point names does not prove every third-party plugin still imports. The oracle for this fixture loads the sample project's own entry points only.
