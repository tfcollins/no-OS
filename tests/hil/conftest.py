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
SUPPORT_DIR = HIL_DIR / "support"
REPO_ROOT = HIL_DIR.parents[1]
if str(SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(SUPPORT_DIR))
if str(HIL_DIR) not in sys.path:
    sys.path.insert(0, str(HIL_DIR))

import reporting  # noqa: E402  (tests/hil/support must be on sys.path first, set just above)



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


def pytest_configure(config):
    # pytest-metadata (bundled with pytest-html) exposes config._metadata; fold
    # in our run-level metadata so it shows in the HTML report header. No-op when
    # pytest-html is not installed.
    md = getattr(config, "_metadata", None)
    if isinstance(md, dict):
        md.update(reporting.run_metadata(config))


@pytest.fixture(autouse=True)
def _record_hil_metadata(request, record_property):
    """Attach per-test metadata to the JUnit XML <properties> for each test."""
    cfg = request.config
    record_property("noos_project", cfg.getoption("--noos-project"))
    record_property("noos_platform", cfg.getoption("--noos-platform"))
    record_property("noos_build", cfg.getoption("--noos-build"))
    record_property("noos_loader", cfg.getoption("--noos-loader"))
    for hw in reporting.marker_values(request.node, "iio_hardware"):
        record_property("iio_hardware", hw)
    for carrier in reporting.marker_values(request.node, "iio_carrier"):
        record_property("iio_carrier", carrier)


@pytest.fixture(scope="session")
def firmware(request, tmp_path_factory):
    """Produce-or-locate boot artifacts. Skips the session if none are available."""
    import builder

    artifacts_opt = request.config.getoption("--noos-artifacts")
    if artifacts_opt:
        root = builder.unpack_if_zip(
            artifacts_opt, tmp_path_factory.mktemp("noos-artifacts"))
        arts = builder.discover_artifacts(root)
    else:
        builds_dir = Path(request.config.getoption("--noos-builds-dir"))
        if not builds_dir.is_absolute():
            builds_dir = REPO_ROOT / builds_dir
        try:
            builder.build_via_build_projects(
                project=request.config.getoption("--noos-project"),
                platform=request.config.getoption("--noos-platform"),
                build_name=request.config.getoption("--noos-build"),
                hardware=request.config.getoption("--noos-hardware"),
                builds_dir=builds_dir,
                export_dir=builds_dir / "export",
                log_dir=builds_dir / "logs",
                python=request.config.getoption("--noos-python"),
            )
        except subprocess.CalledProcessError as exc:
            pytest.fail(f"build_projects.py failed: {exc}")
        arts = builder.discover_artifacts(builds_dir)

    if arts.elf is None and arts.boot_bin is None:
        pytest.skip("no boot artifacts (.elf / BOOT.BIN) available; cannot run on hardware")
    return arts


def _loader_options(config) -> dict:
    return {
        "xsa": config.getoption("--noos-xsa"),
        "xsct": config.getoption("--noos-xsct"),
        "jtag_host": config.getoption("--noos-jtag-host"),
        "jtag_port": config.getoption("--noos-jtag-port"),
        "jtag_cable": config.getoption("--noos-jtag-cable"),
    }


@pytest.fixture
def power(target):
    """labgrid PowerProtocol driver (off()/on()/cycle())."""
    return target.get_driver("PowerProtocol")


@pytest.fixture
def console(target):
    """labgrid ConsoleProtocol driver, with pexpect-style .expect()."""
    drv = target.get_driver("ConsoleProtocol")
    target.activate(drv)
    return drv


@pytest.fixture
def loaded_firmware(request, firmware, target, power, console):
    """Power-cycle the board and load the firmware via the selected loader."""
    from loaders import select_loader

    loader = select_loader(request.config.getoption("--noos-loader"), target)
    if loader.name == "jtag":
        power.cycle()
    loader.load(firmware, target, _loader_options(request.config))
    return {"console": console, "artifacts": firmware, "loader": loader.name}
