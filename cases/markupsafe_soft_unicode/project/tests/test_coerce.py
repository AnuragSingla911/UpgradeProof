from textsafe.coerce import as_text


def test_text_and_number():
    assert as_text("ok") == "ok"
    assert as_text(5) == "5"
