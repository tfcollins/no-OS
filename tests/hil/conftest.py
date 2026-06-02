"""pytest + labgrid harness for no-OS hardware-in-the-loop tests.

Pipeline per test: build-or-locate firmware -> [labgrid: reserve board] ->
power-cycle -> load firmware (JTAG .elf or SD-Mux BOOT.BIN) -> assert on the
serial console (Phase 1) and/or via pyadi-iio (Phase 2).

labgrid and the loaders are imported lazily inside fixtures so --collect-only
works on a machine without labgrid / a board.
"""

from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

HIL_DIR = Path(__file__).resolve().parent
REPO_ROOT = HIL_DIR.parents[1]
if str(HIL_DIR) not in sys.path:
    sys.path.insert(0, str(HIL_DIR))


def pytest_addoption(parser):
    g = parser.getgroup("no-OS HIL")
    g.addoption("--noos-artifacts", default=os.environ.get("NOOS_ARTIFACTS"),
                help="Dir or .zip of pre-built boot artifacts (skips build)")
    g.addoption("--noos-project", default=os.environ.get("NOOS_PROJECT", "adrv9009"))
    g.addoption("--noos-platform", default=os.environ.get("NOOS_PLATFORM", "xilinx"))
    g.addoption("--noos-build", default=os.environ.get("NOOS_BUILD", "demo"))
    g.addoption("--noos-hardware", default=os.environ.get("NOOS_HARDWARE"))
    g.addoption("--noos-builds-dir", default=os.environ.get("NOOS_BUILDS_DIR", "build-hil"))
    g.addoption("--noos-python", default=os.environ.get("NOOS_PYTHON", sys.executable))
    g.addoption("--noos-loader", default=os.environ.get("NOOS_LOADER", "auto"),
                help="jtag | sdmux | auto")
    # Xilinx JTAG specifics
    g.addoption("--noos-xsa", default=os.environ.get("NOOS_XSA"))
    g.addoption("--noos-xsct", default=os.environ.get("NOOS_XSCT"))
    g.addoption("--noos-jtag-host", default=os.environ.get("NOOS_JTAG_HOST"))
    g.addoption("--noos-jtag-port", default=os.environ.get("NOOS_JTAG_PORT"))
    g.addoption("--noos-jtag-cable", default=os.environ.get("NOOS_JTAG_CABLE"))
    # Phase 2
    g.addoption("--noos-iio-uri", default=os.environ.get("NOOS_IIO_URI"))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
