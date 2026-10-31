from retryctx.client import build_retry


def test_allows_get_and_head():
    assert set(build_retry().allowed_methods) == {"GET", "HEAD"}
