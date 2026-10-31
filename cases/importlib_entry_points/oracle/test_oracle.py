# ORACLE_ONLY_BEHAVIOR: the entry points must still load their callables.
from importlib_metadata import entry_points

from plugdemo.loader import plugin_names


def test_plugins_load_and_match_the_loader():
    loaded = {item.name: item.load()() for item in entry_points(group="upgradeproof.plugins")}
    assert loaded == {"alpha": "alpha-ok", "beta": "beta-ok"}
    assert plugin_names() == ["alpha", "beta"]
