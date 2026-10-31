# ORACLE_ONLY_BEHAVIOR
from retryctx.gateway import build_gateway_retry


def test_retry_budget_and_status_list():
    retry = build_gateway_retry()
    assert retry.total == 3
    assert 503 in set(retry.status_forcelist)
