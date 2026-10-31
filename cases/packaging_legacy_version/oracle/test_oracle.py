# ORACLE_ONLY_BEHAVIOR: non-PEP 440 text keeps the legacy label.
from versions.describe import describe


def test_nonstandard_version_keeps_legacy_label():
    assert describe("not a version") == "legacy:not a version"
    assert describe("2.0a1") == "pep440:2.0a1"
