from plugdemo.loader import plugin_names


def test_lists_plugins():
    assert plugin_names() == ["alpha", "beta"]
