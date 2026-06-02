# HIL Testing Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pluggable, pytest-driven hardware-in-the-loop (HIL) flow under `tests/hil/` that produces (or consumes pre-built) no-OS boot files, loads them onto a board via a selectable loader (Xilinx JTAG or SD-Mux), runs C-console and Python/pyadi-iio tests, and emits JUnit XML + pytest-html reports.

**Architecture:** A thin layer over labgrid + `adi-labgrid-plugins`. Pure helper modules (`builder.py`, `loaders/`, `reporting.py`, `jtag_loader.py`) are unit-tested with no hardware; pytest fixtures in `conftest.py` wire them to a labgrid `target`; hardware tests in `tests/hil/tests/` skip cleanly when no board/env is present. Local-bench vs board-farm differ only in the labgrid env YAML.

**Tech Stack:** Python 3, pytest, pytest-html, labgrid, `adi-labgrid-plugins`, pyadi-iio/libiio, Xilinx `xsct` (via existing `util.tcl`), `tools/scripts/build_projects.py`.

**Reference spec:** `docs/superpowers/specs/2026-06-01-hil-testing-flow-design.md`

---

## File Structure

| File | Responsibility |
| --- | --- |
| `tests/hil/builder.py` | `Artifacts` record + discover/unpack/build boot artifacts |
| `tests/hil/jtag_loader.py` | Wrap `util.tcl upload` (xsct) — ported from prototype |
| `tests/hil/loaders/__init__.py` | `Loader` protocol, registry, `select_loader`/`infer_loader_name` |
| `tests/hil/loaders/jtag.py` | `JTAGLoader` — power-cycle + xsct `.elf` load |
| `tests/hil/loaders/sdmux.py` | `SDMuxLoader` — write `BOOT.BIN` to SD-Mux + SD boot |
| `tests/hil/reporting.py` | Pure report-metadata helpers (`run_metadata`, `marker_values`) |
| `tests/hil/conftest.py` | pytest options + fixtures (`firmware`, `power`, `console`, `loaded_firmware`) + report hooks |
| `tests/hil/pytest.ini` | marker registration |
| `tests/hil/requirements-hil.txt` / `requirements-hil-iio.txt` | venv deps |
| `tests/hil/tests/test_boot_console.py` | Phase 1 C/console tests |
| `tests/hil/tests/test_iio_serial.py` | Phase 2 Python/pyadi tests |
| `tests/hil/env/*.yaml` | labgrid env examples (local + coordinator) |
| `tests/hil/test_builder.py` / `test_loaders.py` / `test_reporting.py` / `test_jtag_loader.py` | harness unit tests (no hardware) |
| `.github/workflows/hil.yml` | self-hosted HIL CI |
| `tests/hil/README.md` | how to run locally + on a farm |

**Note on imports:** `conftest.py` inserts `tests/hil/` onto `sys.path`, so both unit tests (in `tests/hil/`) and hardware tests (in `tests/hil/tests/`) import `builder`, `jtag_loader`, `loaders`, `reporting` as top-level modules.

**Run unit tests from the repo root:**
`python -m pytest tests/hil/test_builder.py tests/hil/test_loaders.py tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v`

---

## Task 1: HIL scaffolding (dirs, requirements, pytest.ini, minimal conftest)

**Files:**
- Create: `tests/hil/__init__.py` (empty — not required, skip), `tests/hil/pytest.ini`
- Create: `tests/hil/requirements-hil.txt`, `tests/hil/requirements-hil-iio.txt`
- Create: `tests/hil/conftest.py`
- Create: `tests/hil/loaders/__init__.py` (placeholder, filled in Task 4)

- [ ] **Step 1: Create `tests/hil/pytest.ini`**

```ini
[pytest]
addopts = -ra
# JUnit/HTML report flags are passed on the CI command line (not here) so that
# --collect-only works on a dev machine without pytest-html / labgrid installed.
markers =
    iio_hardware(names): daughter-board / chip families the test exercises
    iio_carrier(names): FPGA carriers the test supports
```

- [ ] **Step 2: Create `tests/hil/requirements-hil.txt`**

```text
# Phase 1 (boot/console) HIL dependencies. Install into a venv:
#   python3 -m venv .hilvenv && ./.hilvenv/bin/pip install -r tests/hil/requirements-hil.txt
pytest>=7
pytest-html>=4
pyserial
labgrid
# ADI labgrid drivers/resources/strategies + iio_hardware/iio_carrier markers.
adi-labgrid-plugins @ git+https://github.com/tfcollins/labgrid-plugins.git
```

- [ ] **Step 3: Create `tests/hil/requirements-hil-iio.txt`**

```text
# Phase 2 (IIO over serial/network) extras. Kept separate because pytest-libiio
# imports libiio at load time.
#   ./.hilvenv/bin/pip install -r tests/hil/requirements-hil-iio.txt
pytest-libiio
pyadi-iio
```

- [ ] **Step 4: Create minimal `tests/hil/conftest.py`** (options + sys.path; fixtures added later)

```python
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
```

- [ ] **Step 5: Create placeholder `tests/hil/loaders/__init__.py`**

```python
"""Loader abstraction (filled in by later tasks)."""
```

- [ ] **Step 6: Verify collection works without hardware**

Run: `python -m pytest tests/hil --collect-only -q`
Expected: exits 0, "no tests ran" (no test files yet) — and **no** error about labgrid/pytest-html.

- [ ] **Step 7: Commit**

```bash
git add tests/hil/pytest.ini tests/hil/requirements-hil.txt tests/hil/requirements-hil-iio.txt tests/hil/conftest.py tests/hil/loaders/__init__.py
git commit -m "test(hil): scaffold HIL harness (options, requirements, pytest config)"
```

---

## Task 2: `Artifacts` record + artifact discovery (builder, pre-built mode)

**Files:**
- Create: `tests/hil/builder.py`
- Test: `tests/hil/test_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/hil/test_builder.py
import zipfile

import pytest

import builder


def test_discover_artifacts_first_match(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "app.elf").write_bytes(b"elf")
    (tmp_path / "sub" / "BOOT.BIN").write_bytes(b"boot")
    arts = builder.discover_artifacts(tmp_path)
    assert arts.elf == tmp_path / "app.elf"
    assert arts.boot_bin == tmp_path / "sub" / "BOOT.BIN"
    assert arts.hex is None
    assert arts.build_dir == tmp_path


def test_require_raises_when_missing(tmp_path):
    arts = builder.discover_artifacts(tmp_path)
    with pytest.raises(FileNotFoundError):
        arts.require("elf")


def test_unpack_if_zip(tmp_path):
    z = tmp_path / "a.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("x.elf", "e")
    dest = tmp_path / "out"
    out = builder.unpack_if_zip(z, dest)
    assert out == dest
    assert (dest / "x.elf").exists()


def test_unpack_if_zip_passthrough_for_dir(tmp_path):
    assert builder.unpack_if_zip(tmp_path, tmp_path / "unused") == tmp_path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_builder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'builder'`

- [ ] **Step 3: Write minimal implementation**

```python
# tests/hil/builder.py
"""Produce or locate no-OS boot artifacts for HIL tests.

build_projects.py's xilinx export ships BOOT.BIN + bootgen_sysfiles.tar.gz but
NOT the .elf, so build mode (Task 3) discovers over the builds_dir (where the
.elf lives), not just the export dir.
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_PROJECTS = REPO_ROOT / "tools" / "scripts" / "build_projects.py"

# Artifacts field -> glob pattern; first sorted match wins.
_ARTIFACT_PATTERNS = {
    "elf": "*.elf",
    "boot_bin": "BOOT.BIN",
    "hex": "*.hex",
    "uf2": "*.uf2",
    "bin": "*.bin",
    "xsa": "*.xsa",
}


@dataclasses.dataclass
class Artifacts:
    build_dir: Path
    elf: Path | None = None
    boot_bin: Path | None = None
    hex: Path | None = None
    uf2: Path | None = None
    bin: Path | None = None
    xsa: Path | None = None

    def require(self, field: str) -> Path:
        value = getattr(self, field)
        if value is None:
            raise FileNotFoundError(f"no {field} artifact found under {self.build_dir}")
        return value


def discover_artifacts(root) -> Artifacts:
    """Recursively find boot artifacts under root; first match per type wins."""
    root = Path(root)
    found = {}
    for field, pattern in _ARTIFACT_PATTERNS.items():
        matches = sorted(root.rglob(pattern))
        if matches:
            found[field] = matches[0]
    return Artifacts(build_dir=root, **found)


def unpack_if_zip(path, dest) -> Path:
    """If path is a .zip, extract into dest and return dest; else return path."""
    path = Path(path)
    if path.suffix == ".zip":
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as z:
            z.extractall(dest)
        return dest
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_builder.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/hil/builder.py tests/hil/test_builder.py
git commit -m "test(hil): add Artifacts record + artifact discovery"
```

---

## Task 3: builder build-mode wrapper around `build_projects.py`

**Files:**
- Modify: `tests/hil/builder.py` (add `build_via_build_projects`)
- Test: `tests/hil/test_builder.py` (add cases)

- [ ] **Step 1: Write the failing test** (append to `tests/hil/test_builder.py`)

```python
def test_build_via_build_projects_argv(tmp_path, monkeypatch):
    calls = {}

    def fake_run(argv, cwd=None, check=None):
        calls["argv"] = argv
        calls["cwd"] = cwd
        calls["check"] = check
        return None

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    out = builder.build_via_build_projects(
        project="adrv9009", platform="xilinx", build_name="demo",
        builds_dir=tmp_path, export_dir=tmp_path / "e", log_dir=tmp_path / "l",
        python="python3", hardware="adrv9009_zc706")
    assert out == tmp_path
    argv = calls["argv"]
    assert argv[0] == "python3"
    assert str(builder.BUILD_PROJECTS) in argv
    assert "-project=adrv9009" in argv
    assert "-platform=xilinx" in argv
    assert "-build_name=demo" in argv
    assert "-hardware=adrv9009_zc706" in argv
    assert f"-builds_dir={tmp_path}" in argv
    assert calls["check"] is True


def test_build_via_build_projects_omits_empty_hardware(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(builder.subprocess, "run",
                        lambda argv, cwd=None, check=None: calls.setdefault("argv", argv))
    builder.build_via_build_projects(
        project="iio_demo", platform="xilinx", build_name="iio_zed",
        builds_dir=tmp_path, export_dir=tmp_path / "e", log_dir=tmp_path / "l")
    assert not any(a.startswith("-hardware=") for a in calls["argv"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_builder.py -k build_via -v`
Expected: FAIL — `AttributeError: module 'builder' has no attribute 'build_via_build_projects'`

- [ ] **Step 3: Write minimal implementation** (append to `tests/hil/builder.py`)

```python
def build_via_build_projects(*, project, platform, build_name, builds_dir,
                             export_dir, log_dir, python=sys.executable,
                             hardware=None) -> Path:
    """Run build_projects.py for one named build. Returns the builds_dir Path.

    Raises subprocess.CalledProcessError on build failure (check=True). After
    this returns, call discover_artifacts(builds_dir) to locate the .elf and
    (for xilinx) the BOOT.BIN.
    """
    builds_dir = Path(builds_dir)
    argv = [
        python, str(BUILD_PROJECTS), str(REPO_ROOT),
        f"-export_dir={export_dir}", f"-log_dir={log_dir}",
        f"-builds_dir={builds_dir}", f"-project={project}",
        f"-platform={platform}", f"-build_name={build_name}",
    ]
    if hardware:
        argv.append(f"-hardware={hardware}")
    subprocess.run(argv, cwd=REPO_ROOT, check=True)
    return builds_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_builder.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/hil/builder.py tests/hil/test_builder.py
git commit -m "test(hil): add build_projects.py build-mode wrapper"
```

---

## Task 4: Loader protocol, registry, and selection

**Files:**
- Modify: `tests/hil/loaders/__init__.py`
- Create: `tests/hil/loaders/jtag.py` (stub class so registry imports), `tests/hil/loaders/sdmux.py` (stub class)
- Test: `tests/hil/test_loaders.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/hil/test_loaders.py
import pytest

import loaders


def _make_target(*type_names):
    """A fake labgrid target whose resources have the given class names."""
    res = [type(name, (), {})() for name in type_names]
    return type("FakeTarget", (), {"resources": res})()


def test_infer_jtag_from_resources():
    t = _make_target("XilinxDeviceJTAG", "NetworkSerialPort")
    assert loaders.infer_loader_name(t) == "jtag"


def test_infer_sdmux_from_resources():
    t = _make_target("USBSDMuxDevice", "NetworkSerialPort")
    assert loaders.infer_loader_name(t) == "sdmux"


def test_infer_raises_when_unknown():
    with pytest.raises(LookupError):
        loaders.infer_loader_name(_make_target("NetworkSerialPort"))


def test_select_explicit_jtag():
    assert loaders.select_loader("jtag", _make_target()).name == "jtag"


def test_select_auto_uses_inference():
    t = _make_target("USBSDMuxDevice")
    assert loaders.select_loader("auto", t).name == "sdmux"


def test_select_unknown_name_raises():
    with pytest.raises(LookupError):
        loaders.select_loader("nope", _make_target())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_loaders.py -v`
Expected: FAIL — `AttributeError: module 'loaders' has no attribute 'infer_loader_name'`

- [ ] **Step 3: Write stub loader classes**

```python
# tests/hil/loaders/jtag.py
"""Xilinx bare-metal JTAG loader (load() implemented in Task 6)."""


class JTAGLoader:
    name = "jtag"

    def load(self, artifacts, target, options) -> None:
        raise NotImplementedError
```

```python
# tests/hil/loaders/sdmux.py
"""Xilinx SD-Mux BOOT.BIN loader (load() implemented in Task 7)."""


class SDMuxLoader:
    name = "sdmux"

    def load(self, artifacts, target, options) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Implement selection in `tests/hil/loaders/__init__.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_loaders.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add tests/hil/loaders/
git add tests/hil/test_loaders.py
git commit -m "test(hil): add Loader protocol, registry, and selection"
```

---

## Task 5: Port `jtag_loader.py` (util.tcl wrapper) with unit tests

**Files:**
- Create: `tests/hil/jtag_loader.py`
- Test: `tests/hil/test_jtag_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/hil/test_jtag_loader.py
import zipfile

import jtag_loader


def test_build_upload_argv_order_and_contents():
    argv = jtag_loader.build_upload_argv(
        xsct="xsct", ws="/ws", hw_path="/hw", hw_basename="design.xsa",
        elf="/build/app.elf", jtag_cable_id="cable1")
    assert argv[:4] == ["xsct", "-nodisp", str(jtag_loader.UTIL_TCL), "upload"]
    assert argv[4:7] == ["/hw", "/hw", "design.xsa"]   # ws hw_path hw_basename
    assert "/build/app.elf" in argv
    assert argv[-1] == "cable1"


def test_stage_hw_path_extracts_bit_and_ps7(tmp_path):
    xsa = tmp_path / "design.xsa"
    with zipfile.ZipFile(xsa, "w") as z:
        z.writestr("ps7_init.tcl", "# ps7 init")
        z.writestr("design_wrapper.bit", b"\x00\x01\x02")
    hw = tmp_path / "hw"
    basename = jtag_loader.stage_hw_path(xsa, hw)
    assert basename == "design.xsa"
    assert (hw / "design.xsa").exists()
    assert (hw / "ps7_init.tcl").read_text() == "# ps7 init"
    assert (hw / "design.bit").read_bytes() == b"\x00\x01\x02"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_jtag_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jtag_loader'`

- [ ] **Step 3: Write the implementation** (ported from the `cmake-xilinx-zcu102` prototype; `REPO_ROOT` resolves to the no-OS root)

```python
# tests/hil/jtag_loader.py
"""Bare-metal JTAG loader for no-OS Xilinx targets.

Thin wrapper around the repo's xsct script
``tools/scripts/platform/xilinx/util.tcl`` (``upload`` proc), which performs the
Zynq-7000 bring-up over JTAG: connect -> reset CPU -> fpga <bitstream> ->
ps7_init -> dow <elf> -> con. We reuse util.tcl rather than re-implement it.

Remote xsct (hardware server on a farm host) is selected via the
XSCT_REMOTE_HOST / XSCT_REMOTE_PORT environment variables, which util.tcl reads.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UTIL_TCL = REPO_ROOT / "tools" / "scripts" / "platform" / "xilinx" / "util.tcl"


def stage_hw_path(xsa_path, hw_path) -> str:
    """Assemble the directory util.tcl loads from an .xsa.

    Copies the .xsa into hw_path and extracts ps7_init.tcl and the bitstream
    (renamed to <stem>.bit, which is what util.tcl expects). Returns the xsa
    basename (util.tcl argv slot).
    """
    xsa_path = Path(xsa_path)
    hw_path = Path(hw_path)
    hw_path.mkdir(parents=True, exist_ok=True)

    staged_xsa = hw_path / xsa_path.name
    shutil.copyfile(xsa_path, staged_xsa)
    stem = xsa_path.stem

    with zipfile.ZipFile(xsa_path) as z:
        names = z.namelist()
        for cand in ("ps7_init.tcl", "psu_init.tcl"):
            if cand in names:
                (hw_path / cand).write_bytes(z.read(cand))
                break
        bits = [n for n in names if n.lower().endswith(".bit")]
        if bits:
            (hw_path / f"{stem}.bit").write_bytes(z.read(bits[0]))

    return staged_xsa.name


def build_upload_argv(*, xsct, ws, hw_path, hw_basename, elf,
                      jtag_cable_id="", target_cpu="0",
                      template="Empty Application(C)", fsbl="0") -> list:
    """Construct the exact xsct argv (mirrors tools/scripts/xilinx.mk).

    Positional order consumed by util.tcl:
      function ws hw_path hw(basename) binary target template fsbl jtagtarget
    """
    return [
        xsct, "-nodisp", str(UTIL_TCL), "upload",
        str(ws), str(hw_path), hw_basename,
        str(elf), str(target_cpu), template, str(fsbl), jtag_cable_id,
    ]


def upload(*, xsa, elf, hw_path, xsct="xsct", jtag_cable_id="",
           remote_host=None, remote_port=None, timeout=600) -> subprocess.CompletedProcess:
    """Stage the .xsa and run util.tcl upload to load+run the .elf."""
    hw_basename = stage_hw_path(xsa, hw_path)
    env = dict(os.environ)
    if remote_host and remote_port:
        env["XSCT_REMOTE_HOST"] = str(remote_host)
        env["XSCT_REMOTE_PORT"] = str(remote_port)
    argv = build_upload_argv(
        xsct=xsct, ws=hw_path, hw_path=hw_path, hw_basename=hw_basename,
        elf=elf, jtag_cable_id=jtag_cable_id)
    return subprocess.run(
        argv, env=env, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_jtag_loader.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/hil/jtag_loader.py tests/hil/test_jtag_loader.py
git commit -m "test(hil): port util.tcl JTAG loader wrapper with unit tests"
```

---

## Task 6: Implement `JTAGLoader.load`

**Files:**
- Modify: `tests/hil/loaders/jtag.py`
- Test: `tests/hil/test_loaders.py` (add cases)

- [ ] **Step 1: Write the failing test** (append to `tests/hil/test_loaders.py`)

```python
def test_jtag_loader_skips_without_xsa(tmp_path):
    import builder
    from loaders.jtag import JTAGLoader
    arts = builder.discover_artifacts(tmp_path)  # no .elf, no .xsa
    with pytest.raises(pytest.skip.Exception):
        JTAGLoader().load(arts, _make_target(), {"xsa": None})


def test_jtag_loader_calls_upload(tmp_path, monkeypatch):
    import builder
    from loaders import jtag as jtag_mod
    elf = tmp_path / "app.elf"
    elf.write_bytes(b"elf")
    xsa = tmp_path / "design.xsa"
    xsa.write_bytes(b"xsa")
    arts = builder.discover_artifacts(tmp_path)

    captured = {}

    class _OK:
        returncode = 0
        stdout = ""

    def fake_upload(**kwargs):
        captured.update(kwargs)
        return _OK()

    monkeypatch.setattr(jtag_mod.jtag_loader, "upload", fake_upload)
    jtag_mod.JTAGLoader().load(
        arts, _make_target(),
        {"xsa": str(xsa), "xsct": "/opt/xsct", "jtag_cable": "c1",
         "jtag_host": "farmhost", "jtag_port": "3121"})
    assert str(captured["elf"]) == str(elf)
    assert str(captured["xsa"]) == str(xsa)
    assert captured["xsct"] == "/opt/xsct"
    assert captured["jtag_cable_id"] == "c1"
    assert captured["remote_host"] == "farmhost"


def test_jtag_loader_fails_on_nonzero_rc(tmp_path, monkeypatch):
    import builder
    from loaders import jtag as jtag_mod
    (tmp_path / "app.elf").write_bytes(b"elf")
    (tmp_path / "design.xsa").write_bytes(b"xsa")
    arts = builder.discover_artifacts(tmp_path)

    class _Fail:
        returncode = 1
        stdout = "xsct error"

    monkeypatch.setattr(jtag_mod.jtag_loader, "upload", lambda **k: _Fail())
    with pytest.raises(pytest.fail.Exception):
        jtag_mod.JTAGLoader().load(arts, _make_target(), {"xsa": str(tmp_path / "design.xsa")})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_loaders.py -k jtag_loader -v`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement `tests/hil/loaders/jtag.py`**

```python
"""Xilinx bare-metal JTAG loader: xsct loads bitstream + ps7_init + .elf."""

from __future__ import annotations

import jtag_loader


class JTAGLoader:
    name = "jtag"

    def load(self, artifacts, target, options) -> None:
        import pytest
        xsa = options.get("xsa") or artifacts.xsa
        if not xsa:
            pytest.skip("jtag loader needs an .xsa (--noos-xsa) and none was found")
        elf = artifacts.require("elf")
        hw_path = artifacts.build_dir / "hil_hw"
        result = jtag_loader.upload(
            xsa=xsa,
            elf=elf,
            hw_path=hw_path,
            xsct=options.get("xsct") or "xsct",
            jtag_cable_id=options.get("jtag_cable") or "",
            remote_host=options.get("jtag_host"),
            remote_port=options.get("jtag_port"),
        )
        if result.returncode != 0:
            pytest.fail(f"JTAG upload failed (rc={result.returncode}):\n{result.stdout}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_loaders.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/hil/loaders/jtag.py tests/hil/test_loaders.py
git commit -m "test(hil): implement JTAGLoader.load"
```

---

## Task 7: Implement `SDMuxLoader.load`

The SD-Mux write + SD boot are validated on hardware (Task 11/CI); the unit test
here covers the clean-skip path when no SD-Mux driver is present in the env.

**Files:**
- Modify: `tests/hil/loaders/sdmux.py`
- Test: `tests/hil/test_loaders.py` (add a case)

- [ ] **Step 1: Write the failing test** (append to `tests/hil/test_loaders.py`)

```python
def test_sdmux_loader_skips_without_driver(tmp_path):
    import builder
    from loaders.sdmux import SDMuxLoader
    (tmp_path / "BOOT.BIN").write_bytes(b"boot")
    arts = builder.discover_artifacts(tmp_path)

    class _NoDriverTarget:
        resources = []

        def get_driver(self, name):
            raise Exception("no such driver")

    with pytest.raises(pytest.skip.Exception):
        SDMuxLoader().load(arts, _NoDriverTarget(), {})


def test_sdmux_loader_requires_boot_bin(tmp_path):
    import builder
    from loaders.sdmux import SDMuxLoader
    arts = builder.discover_artifacts(tmp_path)  # no BOOT.BIN
    with pytest.raises(FileNotFoundError):
        SDMuxLoader().load(arts, _make_target(), {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_loaders.py -k sdmux -v`
Expected: FAIL — `NotImplementedError` (or no FileNotFoundError raised)

- [ ] **Step 3: Implement `tests/hil/loaders/sdmux.py`**

```python
"""Xilinx SD-Mux loader: write BOOT.BIN to the SD card, boot the board from SD.

Uses the adi-labgrid-plugins / labgrid USB SD-Mux storage driver to route the SD
card to the host, copy BOOT.BIN to the FAT boot partition, route it back to the
DUT, then drive the board's boot strategy. The driver/strategy names come from
the labgrid env YAML. If no storage driver is present, the test skips.
"""

from __future__ import annotations


class SDMuxLoader:
    name = "sdmux"

    # Driver names tried, in order, to find the SD-Mux storage driver.
    _STORAGE_DRIVERS = ("USBStorageDriver", "USBSDMuxDriver", "SDMuxDriver")

    def load(self, artifacts, target, options) -> None:
        import pytest
        # require() before touching the target so a missing artifact is a clear error.
        boot_bin = artifacts.require("boot_bin")

        storage = None
        for name in self._STORAGE_DRIVERS:
            try:
                storage = target.get_driver(name)
                break
            except Exception:
                continue
        if storage is None:
            pytest.skip("sdmux loader needs an SD-Mux storage driver in the labgrid env")

        # Route SD to host and write BOOT.BIN to the boot partition root.
        # labgrid's USBStorageDriver exposes write_files(sources, target_dir).
        storage.write_files([str(boot_bin)], target_dir="/")

        # Hand off to the board's boot strategy (adi-labgrid-plugins FPGA SoC /
        # SD boot). The strategy is configured in the env; "boot" is its DUT-up
        # state. PowerProtocol cycling is handled by the strategy transition.
        try:
            strategy = target.get_strategy()
        except Exception:
            pytest.skip("sdmux loader needs a boot strategy in the labgrid env")
        strategy.transition("boot")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_loaders.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/hil/loaders/sdmux.py tests/hil/test_loaders.py
git commit -m "test(hil): implement SDMuxLoader.load (skip-without-driver path tested)"
```

---

## Task 8: Reporting helpers + hooks

**Files:**
- Create: `tests/hil/reporting.py`
- Modify: `tests/hil/conftest.py` (add hooks + autouse fixture)
- Test: `tests/hil/test_reporting.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/hil/test_reporting.py
import reporting


class _FakeConfig:
    def __init__(self, opts):
        self._opts = opts

    def getoption(self, name):
        return self._opts.get(name)


class _FakeMark:
    def __init__(self, args):
        self.args = args


class _FakeItem:
    def __init__(self, marks):
        self._marks = marks

    def iter_markers(self, name):
        return iter(self._marks.get(name, []))


def test_run_metadata():
    cfg = _FakeConfig({
        "--noos-project": "adrv9009", "--noos-platform": "xilinx",
        "--noos-build": "demo", "--noos-loader": "jtag", "--noos-artifacts": None})
    md = reporting.run_metadata(cfg)
    assert md["noOS project"] == "adrv9009"
    assert md["platform"] == "xilinx"
    assert md["loader"] == "jtag"
    assert md["artifacts"] == "(built)"


def test_run_metadata_reports_prebuilt_path():
    cfg = _FakeConfig({"--noos-artifacts": "/tmp/arts.zip"})
    assert reporting.run_metadata(cfg)["artifacts"] == "/tmp/arts.zip"


def test_marker_values_flattens_lists():
    item = _FakeItem({"iio_hardware": [_FakeMark((["adrv9009", "ad9361"],))]})
    assert reporting.marker_values(item, "iio_hardware") == ["adrv9009", "ad9361"]


def test_marker_values_scalars_and_missing():
    item = _FakeItem({"iio_carrier": [_FakeMark(("zc706",))]})
    assert reporting.marker_values(item, "iio_carrier") == ["zc706"]
    assert reporting.marker_values(item, "iio_hardware") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hil/test_reporting.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reporting'`

- [ ] **Step 3: Implement `tests/hil/reporting.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hil/test_reporting.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Wire hooks into `tests/hil/conftest.py`** (append after `repo_root` fixture)

```python
import reporting


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
```

- [ ] **Step 6: Verify the harness unit suite + collection still pass**

Run: `python -m pytest tests/hil/test_builder.py tests/hil/test_loaders.py tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v`
Expected: PASS (all). Then `python -m pytest tests/hil --collect-only -q` exits 0.

- [ ] **Step 7: Commit**

```bash
git add tests/hil/reporting.py tests/hil/test_reporting.py tests/hil/conftest.py
git commit -m "test(hil): add report metadata helpers + JUnit/HTML hooks"
```

---

## Task 9: `firmware`, `power`, `console`, `loaded_firmware` fixtures

**Files:**
- Modify: `tests/hil/conftest.py` (add the four fixtures + loader-options helper)

- [ ] **Step 1: Add the fixtures to `tests/hil/conftest.py`** (append at end)

```python
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
```

- [ ] **Step 2: Verify collection still works without labgrid/hardware**

Run: `python -m pytest tests/hil --collect-only -q`
Expected: exits 0, no errors (fixtures referencing `target` are not invoked at collection time).

- [ ] **Step 3: Re-run the harness unit suite (must still pass)**

Run: `python -m pytest tests/hil/test_builder.py tests/hil/test_loaders.py tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v`
Expected: PASS (all).

- [ ] **Step 4: Commit**

```bash
git add tests/hil/conftest.py
git commit -m "test(hil): add firmware/power/console/loaded_firmware fixtures"
```

---

## Task 10: Phase 1 — C/console hardware tests

**Files:**
- Create: `tests/hil/tests/test_boot_console.py`

These run only on hardware (require the labgrid `target` via `--lg-env`); without
it they error at fixture setup, so they are excluded from unit runs by path.

- [ ] **Step 1: Create `tests/hil/tests/test_boot_console.py`**

```python
"""Phase 1 HIL tests: boot the ADRV9009 firmware and assert on the serial console.

Expected strings are taken verbatim from projects/adrv9009/src/app/*.c. Run on a
board (local bench or farm):

    pytest tests/hil/tests/test_boot_console.py \
        --lg-env tests/hil/env/adrv9009_zc706.yaml \
        -m iio_hardware --noos-project adrv9009 --noos-build demo \
        --noos-xsa /path/adrv9009_zc706.xsa \
        --junit-xml=hil-report.xml --html=hil-report.html --self-contained-html
"""

import pytest

pytestmark = [
    pytest.mark.iio_hardware(["adrv9009"]),
    pytest.mark.iio_carrier(["zc706"]),
]

# Positive boot milestones, in the order the firmware prints them.
BOOT_BANNER = r"Hello"
TALISE_REV = r"talise: Device Revision"
CAL_DONE = r"talise: Calibrations completed successfully"
DONE = r"Bye"

# Failure markers from headless_arm.c / app_*.c; any appearing first -> fail fast.
ERROR_MARKERS = [
    r"error: TALISE_initialize\(\) failed",
    r"error: CLKPLL not locked",
    r"error: RFPLL not locked",
    r"error: Calibrations not completed",
    r"error: TALISE_runInitCals\(\) failed",
    r"error: TALISE_waitInitCals\(\) failed",
    r"error: ad9528_init\(\) failed",
    r"error: .*adxcvr_init\(\) failed",
    r"error: .*axi_jesd204_rx_init_legacy\(\) failed",
    r"error: .*axi_clkgen_init\(\) failed",
    r"axi_dac_init\(\) failed",
    r"axi_adc_init\(\) failed",
]


def _expect_or_error(console, good, timeout):
    """Wait for `good`, failing immediately if any ERROR_MARKER appears first."""
    index, before, _after, _match = console.expect([good] + ERROR_MARKERS, timeout=timeout)
    if index != 0:
        pytest.fail(f"firmware error before {good!r}: matched "
                    f"{ERROR_MARKERS[index - 1]!r}\n--- console ---\n{before}")
    return before


def test_boot_console(loaded_firmware):
    """Firmware boots, Talise initializes + calibrates, and runs to completion."""
    console = loaded_firmware["console"]
    _expect_or_error(console, BOOT_BANNER, timeout=30)
    _expect_or_error(console, TALISE_REV, timeout=60)
    _expect_or_error(console, CAL_DONE, timeout=120)
    _expect_or_error(console, DONE, timeout=60)
```

- [ ] **Step 2: Verify it collects (does not run without a board)**

Run: `python -m pytest tests/hil/tests/test_boot_console.py --collect-only -q`
Expected: exits 0, lists `test_boot_console`, no import error.

- [ ] **Step 3: Commit**

```bash
git add tests/hil/tests/test_boot_console.py
git commit -m "test(hil): add Phase 1 boot/console hardware test (adrv9009/zc706)"
```

---

## Task 11: Phase 2 — Python/pyadi hardware tests

**Files:**
- Create: `tests/hil/tests/test_iio_serial.py`

- [ ] **Step 1: Create `tests/hil/tests/test_iio_serial.py`**

```python
"""Phase 2 HIL tests: talk to the ADRV9009 IIOD (TINYIIOD) with libiio / pyadi-iio.

Requires the Phase-2 extras and an IIOD build (CONFIG_IIO):
    pip install -r tests/hil/requirements-hil-iio.txt
    pytest tests/hil/tests/test_iio_serial.py \
        --lg-env tests/hil/env/adrv9009_zc706.yaml -m iio_hardware \
        --noos-project adrv9009 --noos-build iio --noos-xsa /path/adrv9009_zc706.xsa \
        --noos-iio-uri 'serial:/dev/ttyUSB0,115200'

The libiio serial backend needs a *local* tty; on a farm, expose the target
serial to the runner (ser2net/socat) and pass that URI. If unset, these skip.
The boot console and the libiio serial backend cannot hold the same tty at once,
so run Phase 1 and Phase 2 separately.
"""

import pytest

pytestmark = [
    pytest.mark.iio_hardware(["adrv9009"]),
    pytest.mark.iio_carrier(["zc706"]),
]


@pytest.fixture
def iio_uri(request, loaded_firmware):
    """Resolve the libiio URI for the booted IIOD firmware (or skip)."""
    uri = request.config.getoption("--noos-iio-uri")
    if not uri:
        pytest.skip("no --noos-iio-uri provided for Phase-2 IIO test")
    return uri


def test_iio_context(iio_uri):
    """The IIOD context is reachable and exposes the adrv9009-phy device."""
    iio = pytest.importorskip("iio", reason="libiio python bindings unavailable")
    ctx = iio.Context(iio_uri)
    names = [d.name for d in ctx.devices]
    assert any("adrv9009-phy" in (n or "") for n in names), \
        f"adrv9009-phy not found; devices={names}"


def test_pyadi_adrv9009(iio_uri):
    """pyadi-iio can attach and read a basic attribute."""
    adi = pytest.importorskip("adi", reason="pyadi-iio unavailable")
    dev = adi.adrv9009(uri=iio_uri)
    assert dev.rx_sample_rate > 0
```

- [ ] **Step 2: Verify it collects (does not run without a board/URI)**

Run: `python -m pytest tests/hil/tests/test_iio_serial.py --collect-only -q`
Expected: exits 0, lists both tests, no import error.

- [ ] **Step 3: Commit**

```bash
git add tests/hil/tests/test_iio_serial.py
git commit -m "test(hil): add Phase 2 IIO/pyadi hardware tests (adrv9009/zc706)"
```

---

## Task 12: labgrid env examples (local bench + coordinator)

**Files:**
- Create: `tests/hil/env/adrv9009_zc706_local.example.yaml`
- Create: `tests/hil/env/adrv9009_zc706.example.yaml`

- [ ] **Step 1: Create the coordinator/farm example `tests/hil/env/adrv9009_zc706.example.yaml`**

```yaml
# Example labgrid env: ADRV9009 on ZC706, board-farm / coordinator.
# Copy to adrv9009_zc706.yaml, fill the REPLACE_ME values, then:
#   pytest tests/hil/tests --lg-env tests/hil/env/adrv9009_zc706.yaml \
#     -m iio_hardware --noos-project adrv9009 --noos-build demo \
#     --noos-xsa /path/adrv9009_zc706.xsa
targets:
  main:
    resources:
      RemotePlace:
        name: adrv9009-zc706-bench
      NetworkSerialPort:
        host: REPLACE_ME-exporter-host
        port: 4001
      XilinxDeviceJTAG:
        jtag_cable_id: ""              # "" = first cable
        host: REPLACE_ME-hwserver-host # -> XSCT_REMOTE_HOST (omit for local JTAG)
        port: 3121                     # -> XSCT_REMOTE_PORT (xilinx hw_server default)
      XilinxVivadoTool:
        xsdb_path: /opt/Xilinx/2025.1/Vitis/bin/xsct
      VesyncOutlet:
        outlet_names: "adrv9009-zc706"
        username: "REPLACE_ME@example.com"
        password: "REPLACE_ME"
    drivers:
      SerialDriver: {}                 # ConsoleProtocol for Phase-1 expect()
      VesyncPowerDriver: {}            # PowerProtocol (off/on/cycle)
    options:
      coordinator_address: "REPLACE_ME-coordinator-host:20408"

# Load the ADI plugin drivers/resources/strategies + the iio_* pytest markers:
imports:
  - adi_lg_plugins
```

- [ ] **Step 2: Create the local-bench example `tests/hil/env/adrv9009_zc706_local.example.yaml`**

```yaml
# Example labgrid env: ADRV9009 on ZC706, single local bench (no coordinator).
# Boards attached directly to the machine running pytest. Copy, edit, then:
#   pytest tests/hil/tests --lg-env tests/hil/env/adrv9009_zc706_local.yaml \
#     -m iio_hardware --noos-project adrv9009 --noos-build demo \
#     --noos-xsa /path/adrv9009_zc706.xsa --noos-jtag-cable "" \
#     --noos-xsct /opt/Xilinx/2025.1/Vitis/bin/xsct
targets:
  main:
    resources:
      RawSerialPort:
        port: /dev/ttyUSB0             # board UART on this machine
        speed: 115200
      USBPowerPort:                    # or a NetworkPowerPort / plugin outlet
        match:
          ID_PATH: REPLACE_ME-usb-hub-path
        index: 1
    drivers:
      SerialDriver: {}                 # ConsoleProtocol
      USBPowerDriver: {}               # PowerProtocol (off/on/cycle)

imports:
  - adi_lg_plugins
```

- [ ] **Step 3: Commit**

```bash
git add tests/hil/env/
git commit -m "test(hil): add labgrid env examples (coordinator + local bench)"
```

---

## Task 13: Self-hosted CI workflow

**Files:**
- Create: `.github/workflows/hil.yml`

- [ ] **Step 1: Create `.github/workflows/hil.yml`**

```yaml
# Hardware-in-the-loop tests for no-OS targets (ADRV9009 / ZC706 first).
#
# Runs on a SELF-HOSTED runner with Vitis on PATH, the .xsa design, and network
# access to the labgrid coordinator + board farm. Separate from the Azure
# compile/style CI. Triggered manually or on changes to the Xilinx build, the
# adrv9009 project, or the HIL harness.
name: HIL (ADRV9009 / ZC706)

on:
  workflow_dispatch:
  pull_request:
    paths:
      - 'drivers/platform/xilinx/**'
      - 'drivers/axi_core/**'
      - 'drivers/rf-transceiver/talise/**'
      - 'drivers/frequency/**'
      - 'jesd204/**'
      - 'projects/adrv9009/**'
      - 'tools/scripts/**'
      - 'tests/hil/**'

jobs:
  hil-adrv9009-zc706:
    runs-on: [self-hosted, labgrid, xilinx]
    env:
      XILINX_VITIS: /opt/Xilinx/2025.1/Vitis
      NOOS_XSA: ${{ secrets.ADRV9009_ZC706_XSA }}
      LG_ENV: tests/hil/env/adrv9009_zc706.yaml      # managed on the runner
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }

      - name: Set up HIL venv
        run: |
          python3 -m venv .hilvenv
          ./.hilvenv/bin/pip install -r tests/hil/requirements-hil.txt

      - name: Harness unit tests (no hardware)
        run: |
          ./.hilvenv/bin/pytest \
            tests/hil/test_builder.py tests/hil/test_loaders.py \
            tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v

      - name: Phase 1 - boot/console
        run: |
          PATH="$XILINX_VITIS/bin:$PATH" \
          ./.hilvenv/bin/pytest tests/hil/tests/test_boot_console.py \
            --lg-env "$LG_ENV" -m iio_hardware \
            --noos-project adrv9009 --noos-build demo --noos-xsa "$NOOS_XSA" \
            --junit-xml=hil-phase1.xml --html=hil-phase1.html --self-contained-html

      - name: Phase 2 - IIO over serial
        if: ${{ vars.RUN_HIL_PHASE2 == 'true' }}
        run: |
          ./.hilvenv/bin/pip install -r tests/hil/requirements-hil-iio.txt
          PATH="$XILINX_VITIS/bin:$PATH" \
          ./.hilvenv/bin/pytest tests/hil/tests/test_iio_serial.py \
            --lg-env "$LG_ENV" -m iio_hardware \
            --noos-project adrv9009 --noos-build iio --noos-xsa "$NOOS_XSA" \
            --noos-iio-uri "${{ vars.ADRV9009_ZC706_IIO_URI }}" \
            --junit-xml=hil-phase2.xml --html=hil-phase2.html --self-contained-html

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: hil-reports
          path: |
            hil-phase1.xml
            hil-phase1.html
            hil-phase2.xml
            hil-phase2.html
          if-no-files-found: ignore
```

- [ ] **Step 2: Lint the YAML**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/hil.yml')); print('yaml OK')"`
Expected: `yaml OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/hil.yml
git commit -m "ci(hil): add self-hosted HIL workflow (adrv9009/zc706)"
```

---

## Task 14: README for the HIL flow

**Files:**
- Create: `tests/hil/README.md`

- [ ] **Step 1: Create `tests/hil/README.md`**

````markdown
# no-OS Hardware-in-the-Loop (HIL) tests

A pytest + [labgrid](https://labgrid.org) flow (built on
[`adi-labgrid-plugins`](https://github.com/tfcollins/labgrid-plugins)) that
builds the boot files, loads them onto a board, runs C-console and Python tests,
and emits JUnit XML + HTML reports.

## Layout

- `builder.py` — produce (via `tools/scripts/build_projects.py`) or locate boot artifacts.
- `loaders/` — `jtag` (xsct `.elf` load) and `sdmux` (BOOT.BIN SD boot); selectable.
- `jtag_loader.py` — wraps `tools/scripts/platform/xilinx/util.tcl`.
- `reporting.py` + `conftest.py` — fixtures, options, JUnit/HTML metadata hooks.
- `tests/` — Phase 1 (`test_boot_console.py`, C/console) and Phase 2 (`test_iio_serial.py`, pyadi).
- `env/` — labgrid env examples (coordinator + local bench).
- `test_*.py` (top level) — harness unit tests, run without hardware.

## Install

```bash
python3 -m venv .hilvenv
./.hilvenv/bin/pip install -r tests/hil/requirements-hil.txt
# Phase 2 only:
./.hilvenv/bin/pip install -r tests/hil/requirements-hil-iio.txt
```

## Run

Unit tests (no hardware):

```bash
python -m pytest tests/hil/test_builder.py tests/hil/test_loaders.py \
  tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v
```

On hardware (copy an `env/*.example.yaml` to `env/<name>.yaml` first):

```bash
pytest tests/hil/tests --lg-env tests/hil/env/adrv9009_zc706.yaml \
  -m iio_hardware --noos-project adrv9009 --noos-build demo \
  --noos-xsa /path/adrv9009_zc706.xsa \
  --junit-xml=hil-report.xml --html=hil-report.html --self-contained-html
```

## Key options

| Option | Meaning |
| --- | --- |
| `--noos-artifacts <dir\|zip>` | Use pre-built boot artifacts (skip build) |
| `--noos-project/-platform/-build` | What `build_projects.py` builds |
| `--noos-loader {jtag,sdmux,auto}` | Load mechanism (default `auto`) |
| `--noos-xsa` | Xilinx hardware design (required for JTAG load) |
| `--noos-iio-uri` | libiio URI for Phase 2 (else Phase 2 skips) |
| `--lg-env` | labgrid env YAML (local bench or coordinator) |

## Adding a board / platform

- New board, same platform: add an `env/*.yaml` and mark tests with
  `@pytest.mark.iio_hardware([...])` / `iio_carrier([...])`.
- New flash mechanism (e.g. Maxim OpenOCD, Pico UF2): add a class in `loaders/`
  with a `name` and `load(artifacts, target, options)` method and register it in
  `loaders/__init__.py:_REGISTRY`; extend `infer_loader_name` if needed.
````

- [ ] **Step 2: Commit**

```bash
git add tests/hil/README.md
git commit -m "doc(hil): add HIL flow README"
```

---

## Final verification

- [ ] **Run the full harness unit suite**

Run: `python -m pytest tests/hil/test_builder.py tests/hil/test_loaders.py tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v`
Expected: all PASS (23 tests).

- [ ] **Confirm hardware tests collect cleanly without a board**

Run: `python -m pytest tests/hil --collect-only -q`
Expected: exits 0, lists Phase 1/2 tests and unit tests, no import/plugin errors.

---

## Self-Review (completed during planning)

**Spec coverage:**
- Pluggable framework, Xilinx first → `loaders/` protocol + registry (Tasks 4–7); MCU loaders documented as extension points (README Task 14). ✓
- Build OR pre-built → `builder.py` build-mode + pre-built mode, `firmware` fixture (Tasks 2, 3, 9). ✓
- Selectable JTAG + SD-Mux loader → Tasks 6, 7; selection Task 4. ✓
- JUnit XML + pytest-html → report flags + metadata hooks (Tasks 1, 8, 13). ✓
- Local bench OR coordinator, env-driven → two env examples (Task 12); identical fixtures (Task 9). ✓
- C and Python tests → Phase 1 (Task 10), Phase 2 (Task 11). ✓
- Error handling (build fail / no env skip / load fail / phase-2 skip) → `firmware` fixture skip+fail, loader skip/fail paths (Tasks 6, 7, 9). ✓
- Harness self-tests with no hardware → Tasks 2–8 unit tests. ✓
- CI → Task 13. ✓

**Type/name consistency:** `Artifacts` fields (`elf`, `boot_bin`, `build_dir`, `require`), `Loader.load(artifacts, target, options)`, `select_loader`/`infer_loader_name`, `_loader_options` keys (`xsa`/`xsct`/`jtag_host`/`jtag_port`/`jtag_cable`) match across builder, loaders, fixtures, and tests. `loaded_firmware` returns `{"console", "artifacts", "loader"}`; Phase 1/2 tests read `["console"]`. ✓

**Known integration caveat (not a placeholder):** `SDMuxLoader.load`'s SD write + boot-strategy transition use the installed `adi-labgrid-plugins` driver/strategy API; only the skip-without-driver path is unit-tested, and the write/boot path is validated on hardware in Task 13 / a manual SD-Mux run. The exact storage-driver name is matched from the `_STORAGE_DRIVERS` tuple.
