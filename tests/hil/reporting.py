"""Pure helpers for HIL report metadata. pytest hooks live in conftest.py."""

from __future__ import annotations


def run_metadata(config) -> dict:
    """Run-level metadata for the HTML report header, from CLI options."""
    get = config.getoption
    return {
        "noOS project": get("--noos-project"),
        "platform": get("--noos-platform"),
        "build": get("--noos-build"),
        "loader": get("--noos-loader"),
        "artifacts": get("--noos-artifacts") or "(built)",
    }


def marker_values(item, name) -> list:
    """Flattened args of every marker `name` on a test item (e.g. iio_hardware)."""
    values = []
    for mark in item.iter_markers(name=name):
        for arg in mark.args:
            if isinstance(arg, (list, tuple)):
                values.extend(arg)
            else:
                values.append(arg)
    return values
