# packaging `LegacyVersion`

## When this applies

`packaging` 21.3 parses non-PEP 440 strings into `LegacyVersion`. The class was removed in packaging 22. Importing it on 24.x fails:

`ImportError: cannot import name 'LegacyVersion'`

`parse("not a version")` used to return a legacy object. It now raises `InvalidVersion`.

## Migration

Keep the label `legacy:<text>` for strings the new parser refuses, and keep `pep440:<version>` for strings it accepts:

```python
from packaging.version import InvalidVersion, parse

def describe(version: str) -> str:
    try:
        parsed = parse(version)
    except InvalidVersion:
        return f"legacy:{version}"
    return f"pep440:{parsed}"
```

A repair that only deletes the `LegacyVersion` branch still formats normal versions. It drops the legacy label and fails a behavior check the public test does not cover.

## Executable fence

```upgradeproof-repair
id = "packaging-legacy-version"
package = "packaging"
error_class = "import_error"
error_contains = ["LegacyVersion"]

[[replacements]]
path_glob = "src/**/*.py"
old = '''from packaging.version import LegacyVersion, parse'''
new = '''from packaging.version import InvalidVersion, parse'''

[[replacements]]
path_glob = "src/**/*.py"
old = '''    parsed = parse(version)
    if isinstance(parsed, LegacyVersion):
        return f"legacy:{parsed}"
    return f"pep440:{parsed}"'''
new = '''    try:
        parsed = parse(version)
    except InvalidVersion:
        return f"legacy:{version}"
    return f"pep440:{parsed}"'''
```

## What a passing test does not mean

Preserving two labels is not the same as promising that every legacy ordering quirk from packaging 21 still exists.
