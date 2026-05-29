"""pytest + labgrid fixtures for no-OS Xilinx hardware-in-the-loop tests.

Pipeline per session:
  build firmware (CMake) -> [labgrid: reserve board] -> power cycle ->
  JTAG-load the .elf (util.tcl via jtag_loader) -> assert on serial console.

labgrid is imported lazily inside fixtures so that ``--collect-only`` and the
marker-export dry run work on a machine without labgrid installed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import jtag_loader

REPO_ROOT = Path(__file__).resolve().parents[2]


def pytest_addoption(parser):
    g = parser.getgroup("no-OS HIL")
    g.addoption("--noos-xsa", default=os.environ.get("NOOS_XSA"),
                help="Path to the .xsa hardware design (required to build/load on hardware)")
    g.addoption("--noos-preset", default=os.environ.get("NOOS_PRESET", "adrv9009_zc706"),
                help="CMake board preset to build")
    g.addoption("--noos-project", default=os.environ.get("NOOS_PROJECT", "adrv9009"),
                help="no-OS project name (-DPROJECT_NAME / project.conf)")
    g.addoption("--noos-build-dir", default=os.environ.get("NOOS_BUILD_DIR", "build-hil"),
                help="CMake build directory (relative to repo root unless absolute)")
    g.addoption("--noos-vitis", default=os.environ.get("XILINX_VITIS", "/opt/Xilinx/2025.1/Vitis"),
                help="Vitis install dir (provides xsct, ninja, cross toolchain)")
    g.addoption("--noos-python", default=os.environ.get("NOOS_PYTHON", "/usr/bin/python3"),
                help="Python interpreter for the no-OS venv (must produce a working venv)")
    g.addoption("--noos-iio-uri", default=os.environ.get("NOOS_IIO_URI"),
                help="libiio URI for Phase-2 IIO tests, e.g. 'serial:/dev/ttyUSB0,115200'. "
                     "On a board farm the target serial must be reachable from the runner "
                     "(e.g. ser2net/socat); if unset, Phase-2 tests skip.")


def _vitis_env(vitis: str) -> dict:
    env = dict(os.environ)
    env["XILINX_VITIS"] = vitis
    env["PATH"] = f"{vitis}/bin:" + env.get("PATH", "")
    return env


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def firmware(request, repo_root) -> dict:
    """Build the firmware with CMake and return paths.

    Skips the session if no .xsa is provided (cannot generate the BSP / link).
    Returns {"elf": Path, "xsa": Path, "build_dir": Path}.
    """
    xsa = request.config.getoption("--noos-xsa")
    if not xsa:
        pytest.skip("no --noos-xsa provided; cannot build/flash on hardware")
    xsa = Path(xsa).resolve()
    if not xsa.is_file():
        pytest.skip(f"--noos-xsa not found: {xsa}")

    preset = request.config.getoption("--noos-preset")
    project = request.config.getoption("--noos-project")
    vitis = request.config.getoption("--noos-vitis")
    python = request.config.getoption("--noos-python")
    build_dir = Path(request.config.getoption("--noos-build-dir"))
    if not build_dir.is_absolute():
        build_dir = repo_root / build_dir

    env = _vitis_env(vitis)
    configure = [
        "cmake", "-B", str(build_dir), "--preset", preset,
        f"-DPROJECT_NAME={project}",
        f"-DPROJECT_DEFCONFIG={project}/project.conf",
        f"-DXSA_PATH={xsa}",
        f"-DPython3_EXECUTABLE={python}",
    ]
    subprocess.run(configure, cwd=repo_root, env=env, check=True)
    subprocess.run(["cmake", "--build", str(build_dir)], cwd=repo_root, env=env, check=True)

    elf = build_dir / "build" / f"{project}.elf"
    assert elf.is_file(), f"build did not produce {elf}"
    return {"elf": elf, "xsa": xsa, "build_dir": build_dir}


# --- labgrid-backed fixtures (the `target` fixture comes from labgrid's pytest
#     plugin when --lg-env is given) -------------------------------------------

def _jtag_attrs(target):
    """Pull optional JTAG/xsct attributes from labgrid resources, with defaults."""
    attrs = {"xsct": "xsct", "jtag_cable_id": "", "remote_host": None, "remote_port": None}
    try:
        from labgrid.resource import NetworkSerialPort  # noqa: F401
    except Exception:
        pass
    # XilinxVivadoTool / XilinxDeviceJTAG are provided by adi-labgrid-plugins;
    # access defensively since field names may evolve.
    for res in getattr(target, "resources", []):
        cls = type(res).__name__
        if cls == "XilinxVivadoTool":
            attrs["xsct"] = getattr(res, "xsdb_path", None) or getattr(res, "xsct_path", None) or attrs["xsct"]
        if cls == "XilinxDeviceJTAG":
            attrs["jtag_cable_id"] = getattr(res, "jtag_cable_id", "") or attrs["jtag_cable_id"]
            attrs["remote_host"] = getattr(res, "host", None)
            attrs["remote_port"] = getattr(res, "port", None)
    return attrs


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
    """Power-cycle the board and JTAG-load the firmware, ready to read console."""
    attrs = _jtag_attrs(target)
    hw_path = firmware["build_dir"] / "hil_hw"

    power.cycle()

    result = jtag_loader.upload(
        xsa=firmware["xsa"],
        elf=firmware["elf"],
        hw_path=hw_path,
        xsct=attrs["xsct"],
        jtag_cable_id=attrs["jtag_cable_id"],
        remote_host=attrs["remote_host"],
        remote_port=attrs["remote_port"],
    )
    if result.returncode != 0:
        pytest.fail(f"JTAG upload failed (rc={result.returncode}):\n{result.stdout}")
    return {"console": console, **firmware}
