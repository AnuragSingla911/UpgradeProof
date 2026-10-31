from markupsafe import soft_unicode


def as_text(value: object) -> str:
    return str(soft_unicode(value))
