# Hardware-in-the-Loop Testing Flow — Design

**Date:** 2026-06-01
**Status:** Approved (pending spec review)
**Repo:** no-OS (`dev/testing` branch)

## Problem

no-OS needs a repeatable hardware-in-the-loop (HIL) testing flow that:

1. Builds the boot files for a project (or consumes pre-built ones).
2. Gets that firmware running on real hardware.
3. Runs tests — written in **C** (assertions on firmware console output) or **Python**
   (functional checks via pyadi-iio / libiio) — against the live board.
4. Generates reports consumable by CI and humans.

The flow is built on [`tfcollins/labgrid-plugins`](https://github.com/tfcollins/labgrid-plugins)
(`adi-labgrid-plugins`), which extends upstream labgrid with ADI-specific power control
(VeSync, CyberPower), serial XMODEM, SD-Mux storage, Xilinx JTAG/Vivado resources, boot
strategies, and `iio_hardware` / `iio_carrier` pytest markers for board-farm test selection.

## Prior art

A narrow prototype already exists on the `cmake-xilinx-zcu102` branch
(commits `ead312a66`, `dca2a0376`) under `tests/hil/`:

- pytest + labgrid + `adi_lg_plugins`, fixtures `firmware` / `power` / `console` / `loaded_firmware`.
- Phase 1 C tests (`test_boot_console.py`): power-cycle → JTAG-load `.elf` → `expect()` on console.
- Phase 2 Python tests (`test_iio_serial.py`): pyadi-iio / libiio over UART.
- `jtag_loader.py` wrapping `tools/scripts/platform/xilinx/util.tcl`.
- Self-hosted GitHub Actions workflow `hil-xilinx.yml`.

That prototype is **Xilinx/ADRV9009/ZC706-only**, builds with **CMake** (which does not exist on
`dev/testing` — this branch uses Make + `tools/scripts/build_projects.py` + per-project
`builds.json`), and has **no report generation**. This design ports it onto the Make build path
and generalizes it.

## Decisions (locked)

| Decision | Choice |
| --- | --- |
| Platform scope | Pluggable framework, **Xilinx as first implementation** |
| Build path | **Support both**: consume pre-built artifacts *or* invoke `build_projects.py` |
| Load mechanism | **Both, selectable per board**: JTAG `.elf` and SD-Mux `BOOT.BIN`, via a `Loader` abstraction |
| Reporting | **JUnit XML + pytest-html** baseline (no dashboard/REST integration yet) |
| Execution env | **Both, env-file driven**: local bench *or* coordinator/farm, chosen by labgrid env YAML; self-hosted GitHub Actions |
| Overall shape | **pytest-centric** with thin `builder` + `Loader` abstractions (not a standalone CLI, not pure labgrid strategies) |

## Architecture

All code lives in `tests/hil/`:

```
tests/hil/
  conftest.py            # pytest options + fixtures: firmware, target, power, console, loaded_firmware
  builder.py             # produce-or-locate boot artifacts (build_projects.py / make / pre-built)
  loaders/
    __init__.py          # Loader protocol + registry + selection from env/CLI
    jtag.py              # Xilinx JTAG .elf load (wraps existing jtag_loader.py / util.tcl)
    sdmux.py             # Xilinx SD-Mux BOOT.BIN boot (labgrid-plugins SD-Mux + boot strategy)
  reporting.py           # pytest hooks: per-test metadata + console transcript -> JUnit/HTML
  env/                   # labgrid env YAMLs (local-bench + coordinator examples, per board)
  tests/
    test_boot_console.py # Phase 1 "C" tests: assert on firmware printf over serial
    test_iio_serial.py   # Phase 2 "Python" tests: pyadi-iio / libiio functional checks
  pytest.ini
  requirements-hil.txt
  requirements-hil-iio.txt
  jtag_loader.py         # ported from prototype; reused by loaders/jtag.py
```

### Components

**Builder** (`builder.py`, session-scoped `firmware` fixture). Normalizes output into one
`Artifacts` object `{elf, boot_bin, hex, uf2, xsa, build_dir}` (fields present only when produced):

- *Pre-built mode* — `--noos-artifacts <dir|zip>`: unpack and discover artifacts; no build.
- *Build mode* — wrap `tools/scripts/build_projects.py` for `--noos-project` / `--noos-platform`
  / `--noos-build` (handles `.xsa` hardware-file download and artifact export), with a direct
  `make PLATFORM=... HARDWARE=...` fallback for a single project.
- Skips the session (not fails) when neither artifacts nor a buildable spec is provided, so
  `--collect-only` works on a machine without toolchains.

**Loader** (`loaders/`). A `Loader` protocol with a single method `load(artifacts, target)` that
makes the firmware run on the board (power handled by the `power` fixture / loader):

- `JTAGLoader` (`loaders/jtag.py`) — reuse `jtag_loader.py` + `util.tcl`: power-cycle → bitstream
  + `ps7_init` + `dow <elf>` + `con`. First implementation.
- `SDMuxLoader` (`loaders/sdmux.py`) — write `BOOT.BIN` to SD via the plugin's SD-Mux, flip mux
  to board, power-cycle, boot from SD.
- Selection: `--noos-loader {jtag,sdmux,auto}`; `auto` infers from which resources the env
  exposes. MCU loaders (OpenOCD/J-Link for Maxim/STM32, UF2 for Pico) are documented extension
  points implementing the same protocol — not built now.

**labgrid layer** (`conftest.py` + `env/`). Local-bench vs farm differ **only** in the env YAML:

- Local bench: `RawSerialPort` + `USBPowerPort` (or similar) directly attached.
- Coordinator/farm: `RemotePlace` reservation + `NetworkSerialPort` + `Vesync`/`CyberPower` power.

Fixtures `power` / `console` / `target` are identical across both. Every env imports
`adi_lg_plugins`. labgrid is imported lazily inside fixtures so collection works without it.

**Test layers** (the "C or Python" split; tests carry `iio_hardware` / `iio_carrier` markers):

- **Phase 1 — C/firmware tests** (`test_boot_console.py`): the test logic *is* the C firmware;
  pytest observes the serial console — `expect()` ordered boot milestones, fail-fast on a list of
  error markers, capture boot timing.
- **Phase 2 — Python tests** (`test_iio_serial.py`): pyadi-iio / libiio attach to the running
  IIOD build and run functional checks (context devices present, sample rate, attribute R/W,
  optional data capture). Skips (does not fail) when the transport URI is unavailable.

**Reporting** (`reporting.py`). pytest hooks attach `project · platform · build · hardware ·
carrier · loader · elf` metadata to every test in both JUnit XML and pytest-html; the serial
console transcript is attached to the HTML report on failure; JUnit XML is emitted for native
GitHub/Azure rendering. No dashboard/REST integration in this iteration.

### Data flow

```
builds.json ──(build_projects.py | pre-built)──► Artifacts{elf, BOOT.BIN, xsa}
        │
env YAML (local OR coordinator) ──► target: power · console · sd-mux · xsct/jtag
        │
loaded_firmware: power-cycle ──► Loader.load()   [JTAG .elf  |  SD-Mux BOOT.BIN]
        │
        ├─ Phase 1 (C):      console.expect(milestones, error_markers)
        └─ Phase 2 (Python): pyadi-iio / libiio  ──► functional asserts
        │
pytest hooks ──► JUnit XML  +  pytest-html  (metadata + console transcript + boot timing)
```

## Configuration surface

CLI options (with `NOOS_*` env equivalents), extending the prototype's `--noos-*` set:

- `--noos-artifacts <dir|zip>` — pre-built boot artifacts (skip build).
- `--noos-project`, `--noos-platform`, `--noos-build` — what to build via `build_projects.py`.
- `--noos-loader {jtag,sdmux,auto}` — load mechanism (default `auto`).
- `--noos-iio-uri` — libiio URI for Phase 2 (e.g. `serial:/dev/ttyUSB0,115200`); unset → Phase 2 skips.
- Xilinx/JTAG overrides retained from the prototype (`--noos-xsa`, `--noos-vitis`, `--noos-xsct`,
  `--noos-jtag-host/-port/-cable`).
- Report paths: `--junit-xml`, pytest-html `--html`.

`--lg-env <yaml>` (labgrid's own option) selects the bench/farm.

## Error handling

| Condition | Behavior |
| --- | --- |
| Build failure | Session fails; build log captured/attached. |
| No env / no board / no labgrid | Tests **skip** (collection still works on any dev machine). |
| Load failure (JTAG rc≠0, SD/boot timeout) | Fail fast; captured loader output attached. |
| Error marker on console | Fail immediately; serial transcript attached. |
| Phase-2 transport unavailable | **Skip**, not fail. |

## Testing the harness itself (no hardware)

- Unit-test `builder` artifact discovery against a fake export dir / zip.
- Unit-test `Loader` selection + dispatch with fake loaders/targets.
- Unit-test the report-metadata hook with a stub pytest item.

The hardware tests (Phase 1/2) are the integration layer and run only on a self-hosted runner.

## CI

Generalize the prototype's `hil-xilinx.yml` into `hil.yml`, triggered on `tests/hil/**` and
relevant driver/project paths, on a self-hosted runner (`[self-hosted, labgrid, xilinx]`):

1. Set up HIL venv (`requirements-hil.txt`, optionally `requirements-hil-iio.txt`).
2. Build or fetch artifacts (`build_projects.py` or `--noos-artifacts`).
3. Marker export → matrix (`--hw-ci-export-markers`, intersect with live coordinator places).
4. Phase 1 (boot/console).
5. Phase 2 (IIO), conditional.
6. Upload JUnit XML + pytest-html; publish test summary.

## Scope guards (YAGNI)

- Only Xilinx loaders (`jtag`, `sdmux`) implemented now; MCU loaders are documented extension points.
- Do **not** rewrite `build_projects.py` — wrap it.
- Do **not** reimplement the JTAG sequence — reuse `util.tcl` via `jtag_loader.py`.
- No dashboard / REST coordinator integration in this iteration.

## Out of scope

- Non-Xilinx flashing implementations.
- Trend-history dashboards.
- Changes to the existing Azure compile/style CI.
