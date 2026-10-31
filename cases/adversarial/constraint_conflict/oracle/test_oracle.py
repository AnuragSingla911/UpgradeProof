# ORACLE_ONLY_BEHAVIOR
from pins.report import major_version


def test_not_used_when_resolution_fails():
    assert major_version() == 1
