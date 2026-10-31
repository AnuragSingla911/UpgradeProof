# Werkzeug `url_quote`

## When this applies

Werkzeug 3.0 removed `werkzeug.urls.url_quote`. Version 2.3 still provides it and warns. The failure on 3.x is:

`ImportError: cannot import name 'url_quote' from 'werkzeug.urls'`

## Migration

`urllib.parse.quote` is the documented replacement. Werkzeug treated RFC 3986 sub-delimiters, including `+`, as safe, and also treated `/` and `:` as safe. Plain `quote(value)` encodes `+` as `%2B`, so the safe set has to travel with the call:

```python
from urllib.parse import quote

def encode_query_value(value: str) -> str:
    return quote(value, safe="/:!$'()*+,;")
```

## Executable fence

```upgradeproof-repair
id = "werkzeug-url-quote"
package = "werkzeug"
error_class = "import_error"
error_contains = ["url_quote"]

[[replacements]]
path_glob = "src/**/*.py"
old = '''from werkzeug.urls import url_quote'''
new = '''from urllib.parse import quote'''

[[replacements]]
path_glob = "src/**/*.py"
old = '''return url_quote(value)'''
new = '''return quote(value, safe="/:!$'()*+,;")'''
```

## What a passing test does not mean

Matching `quote` on the strings in the suite does not prove every previous `url_quote` option (`charset`, `unsafe`) still behaves the same.
