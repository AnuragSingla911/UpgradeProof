# ORACLE_ONLY_BEHAVIOR
from textsafe.coerce import as_text


def test_none_becomes_text():
    assert as_text(None) == "None"
