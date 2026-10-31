from pins.report import major_version


def test_baseline_is_urllib3_1():
    assert major_version() == 1
