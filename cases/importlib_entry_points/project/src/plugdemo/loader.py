from importlib_metadata import entry_points


def plugin_names() -> list[str]:
    selected = entry_points()["upgradeproof.plugins"]
    return sorted(entry.name for entry in selected)
