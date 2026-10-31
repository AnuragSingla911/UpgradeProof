from retryctx.gateway import build_gateway_retry


def test_allows_get_and_head():
    assert set(build_gateway_retry().allowed_methods) == {"GET", "HEAD"}
