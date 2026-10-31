# ORACLE_ONLY_BEHAVIOR: nested payloads round-trip and a tampered token is rejected.
import pytest

from tokens.issuer import issue, read


def test_nested_payload_and_tamper():
    token = issue({"user": "ada", "roles": ["a", "b"]}, "s3")
    assert read(token, "s3")["roles"] == ["a", "b"]
    with pytest.raises(Exception):
        read(token + "x", "s3")
