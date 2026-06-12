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
