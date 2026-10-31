import urllib3


def major_version() -> int:
    return int(urllib3.__version__.split(".", 1)[0])
