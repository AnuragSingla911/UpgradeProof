from versions.describe import describe


def test_pep440_release():
    assert describe("1.2.3") == "pep440:1.2.3"
