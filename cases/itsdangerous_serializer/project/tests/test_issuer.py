from tokens.issuer import issue, read


def test_round_trip():
    token = issue({"user": "ada"}, "secret")
    assert isinstance(token, str)
    assert read(token, "secret") == {"user": "ada"}
