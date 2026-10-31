# ORACLE_ONLY_BEHAVIOR
from retryctx.client import build_retry


def test_budget_survives_the_bump():
    retry = build_retry()
    assert retry.total == 3
    assert 503 in set(retry.status_forcelist)
