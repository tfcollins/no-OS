****************************************
Hardware-in-the-Loop (HIL) Testing
****************************************

no-OS includes a pytest + `labgrid <https://labgrid.org>`_ hardware-in-the-loop
(HIL) test flow under ``tests/hil/``, built on the
`adi-labgrid-plugins <https://github.com/tfcollins/labgrid-plugins>`_ package.
It builds (or consumes pre-built) boot files, loads them onto a board, runs
tests written in C (assertions on the firmware serial console) or Python
(functional checks via pyadi-iio / libiio), and emits JUnit XML and self
contained HTML reports.

The same test code runs against a single local bench or a shared board farm
behind a labgrid coordinator; only the labgrid environment YAML differs.

.. note::
   The first implemented platform is Xilinx (ADRV9009 / ZC706). The loader layer
   is pluggable, so other platforms can be added without changing the test code.

Layout
======

.. code-block::

    tests/hil/
    ├── builder.py            # build (build_projects.py) or locate boot artifacts
    ├── jtag_loader.py        # wraps tools/scripts/platform/xilinx/util.tcl
    ├── loaders/              # jtag (.elf via xsct) and sdmux (BOOT.BIN SD boot)
    ├── reporting.py          # JUnit/HTML metadata hooks
    ├── conftest.py           # pytest options + fixtures
    ├── env/                  # labgrid env examples (coordinator + local bench)
    ├── tests/                # Phase 1 (C/console) and Phase 2 (Python/pyadi)
    └── test_*.py             # harness unit tests (run without hardware)

Prerequisites
=============

Create a virtual environment and install the Phase 1 (boot/console)
dependencies:

.. code-block:: bash

    $ python3 -m venv .hilvenv
    $ ./.hilvenv/bin/pip install -r tests/hil/requirements-hil.txt

For the Phase 2 (IIO) tests, also install the extras:

.. code-block:: bash

    $ ./.hilvenv/bin/pip install -r tests/hil/requirements-hil-iio.txt

For the Xilinx JTAG loader, the Vitis ``xsct`` tool must be available (either on
``PATH`` or passed via ``--noos-xsct``). See :doc:`build_xilinx`.

Harness unit tests (no hardware)
================================

The harness logic (builder, loaders, reporting) is unit-tested and runs without
a board or labgrid:

.. code-block:: bash

    $ python3 -m pytest tests/hil/test_builder.py tests/hil/test_loaders.py \
          tests/hil/test_reporting.py tests/hil/test_jtag_loader.py -v

Running on hardware
===================

Copy one of the example environment files and fill in the ``REPLACE_ME`` values:

- ``tests/hil/env/adrv9009_zc706.example.yaml`` — board farm / coordinator
  (``RemotePlace``, networked serial, remote JTAG, smart-outlet power).
- ``tests/hil/env/adrv9009_zc706_local.example.yaml`` — single local bench
  (directly attached serial and USB power).

Then run the Phase 1 boot/console test, building the firmware and loading it
over JTAG:

.. code-block:: bash

    $ pytest tests/hil/tests/test_boot_console.py \
          --lg-env tests/hil/env/adrv9009_zc706.yaml \
          -m iio_hardware --noos-project adrv9009 --noos-build demo \
          --noos-xsa /path/adrv9009_zc706.xsa \
          --junit-xml=hil-report.xml --html=hil-report.html --self-contained-html

The Phase 2 IIO tests talk to a running IIOD build via libiio / pyadi-iio:

.. code-block:: bash

    $ pytest tests/hil/tests/test_iio_serial.py \
          --lg-env tests/hil/env/adrv9009_zc706.yaml -m iio_hardware \
          --noos-project adrv9009 --noos-build iio \
          --noos-xsa /path/adrv9009_zc706.xsa \
          --noos-iio-uri 'serial:/dev/ttyUSB0,115200'

.. note::
   The boot console and the libiio serial backend cannot hold the same tty at
   once, so run Phase 1 and Phase 2 as separate invocations.

Key options
===========

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Option
     - Meaning
   * - ``--noos-artifacts <dir|zip>``
     - Use pre-built boot artifacts (skip the build step).
   * - ``--noos-project`` / ``--noos-platform`` / ``--noos-build``
     - What ``build_projects.py`` builds (project, platform, ``builds.json`` name).
   * - ``--noos-loader {jtag,sdmux,auto}``
     - Firmware load mechanism (default ``auto``, inferred from the env resources).
   * - ``--noos-xsa``
     - Xilinx hardware design ``.xsa`` (required for the JTAG loader).
   * - ``--noos-iio-uri``
     - libiio URI for Phase 2 (if unset, the Phase 2 tests skip).
   * - ``--lg-env``
     - labgrid environment YAML (selects local bench or coordinator/farm).

Reports
=======

Passing ``--junit-xml`` and ``--html`` produces a JUnit XML file (rendered
natively by GitHub Actions / Azure Pipelines) and a self-contained HTML report.
Each test carries ``project``, ``platform``, ``build``, ``loader``, and the
``iio_hardware`` / ``iio_carrier`` markers as metadata.

Continuous integration
======================

The ``.github/workflows/hil.yml`` workflow runs the harness on a self-hosted
runner (with Vitis and board-farm access): harness unit tests, then Phase 1, then
optionally Phase 2, uploading the JUnit and HTML reports as artifacts.

Adding a board or platform
===========================

- **New board, same platform:** add an ``env/*.yaml`` and mark the tests with
  ``@pytest.mark.iio_hardware([...])`` / ``iio_carrier([...])``.
- **New load mechanism** (for example Maxim OpenOCD or Pico UF2): add a class in
  ``tests/hil/loaders/`` with a ``name`` and a
  ``load(artifacts, target, options)`` method, register it in
  ``loaders/__init__.py``, and extend ``infer_loader_name`` if needed.
