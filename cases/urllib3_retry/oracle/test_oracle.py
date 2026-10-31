# ORACLE_ONLY_BEHAVIOR: status list and budget must survive the keyword rename.
from retryctx.client import build_retry


def test_retry_budget_and_status_list():
    retry = build_retry()
    assert retry.total == 3
    assert 503 in set(retry.status_forcelist)
    assert set(retry.allowed_methods) == {"GET", "HEAD"}
