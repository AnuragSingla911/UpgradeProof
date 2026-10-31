from queryesc.encode import encode_query_value


def test_space_and_slash():
    assert encode_query_value("a b") == "a%20b"
    assert encode_query_value("a/b?") == "a/b%3F"
