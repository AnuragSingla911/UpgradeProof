from urllib3.util.retry import Retry


def build_gateway_retry() -> Retry:
    return Retry(total=3, method_whitelist=["GET", "HEAD"], status_forcelist=[503])
