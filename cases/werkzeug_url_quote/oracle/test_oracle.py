# ORACLE_ONLY_BEHAVIOR: '+' stays unescaped, matching Werkzeug's safe set.
from queryesc.encode import encode_query_value


def test_preserves_werkzeug_safe_set():
    assert encode_query_value("a+b") == "a+b"
    assert encode_query_value("a&b") == "a%26b"
    assert encode_query_value("ü") == "%C3%BC"
