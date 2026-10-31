from urllib3.util.retry import Retry


def build_retry() -> Retry:
    return Retry(total=3, allowed_methods=["GET", "HEAD"], status_forcelist=[503])
