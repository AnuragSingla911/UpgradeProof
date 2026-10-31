# ORACLE_ONLY_BEHAVIOR
from app.counter import value


def test_oracle_not_consulted_when_baseline_fails():
    assert value() == 1
