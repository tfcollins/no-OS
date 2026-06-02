"""Loader abstraction: get firmware running on a board.

A Loader implements ``load(artifacts, target, options) -> None``. Loaders are
registered by name; select_loader() picks one explicitly (--noos-loader) or
infers it ('auto') from the resources the labgrid target exposes.
"""

from __future__ import annotations

from typing import Protocol

from .jtag import JTAGLoader
from .sdmux import SDMuxLoader


class Loader(Protocol):
    name: str

    def load(self, artifacts, target, options) -> None: ...


_REGISTRY = {
    JTAGLoader.name: JTAGLoader,
    SDMuxLoader.name: SDMuxLoader,
}


def _resource_names(target) -> set:
    return {type(r).__name__ for r in getattr(target, "resources", [])}


def infer_loader_name(target) -> str:
    """auto: SD-Mux present -> sdmux; Xilinx JTAG/Vivado present -> jtag."""
    names = _resource_names(target)
    if {"USBSDMuxDevice", "SDMux"} & names:
        return SDMuxLoader.name
    if {"XilinxDeviceJTAG", "XilinxVivadoTool"} & names:
        return JTAGLoader.name
    raise LookupError(f"cannot infer loader from resources: {sorted(names)}")


def select_loader(name, target):
    """Return a Loader instance for `name` ('auto' infers from the target)."""
    if name in (None, "", "auto"):
        name = infer_loader_name(target)
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise LookupError(f"unknown loader {name!r}; known: {sorted(_REGISTRY)}")
