# MarkupSafe `soft_unicode`

## When this applies

MarkupSafe 2.0 renamed `soft_unicode` to `soft_str` and 2.1 removed the old name. Importing `soft_unicode` on 2.1.5 raises `ImportError`.

## Migration a maintainer could promote

```python
from markupsafe import soft_str

def as_text(value: object) -> str:
    return str(soft_str(value))
```

## No executable fence

This file is prose and an example. It intentionally has no `upgradeproof-repair` fence, and there is no promoted rule for MarkupSafe.

Rules mode and skill mode must abstain. They must not invent `soft_str` from the example above. A later maintainer can add a fence only after a verified run shows the replacement preserves behavior.

## What a passing test would not mean

Coercing a string and an integer would not prove every Markup object in a template still escapes the same way.
