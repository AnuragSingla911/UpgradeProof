from werkzeug.urls import url_quote


def encode_query_value(value: str) -> str:
    return url_quote(value)
