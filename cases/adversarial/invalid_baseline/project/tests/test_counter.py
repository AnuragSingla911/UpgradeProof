from app.counter import value


def test_value_matches_the_documented_contract():
    assert value() == 0
