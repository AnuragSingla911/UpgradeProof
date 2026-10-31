from packaging.version import LegacyVersion, parse


def describe(version: str) -> str:
    parsed = parse(version)
    if isinstance(parsed, LegacyVersion):
        return f"legacy:{parsed}"
    return f"pep440:{parsed}"
