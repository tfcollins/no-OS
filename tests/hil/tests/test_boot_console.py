"""Phase 1 HIL tests: boot the ADRV9009 firmware on ZC706 and assert on the
serial console output.

Expected strings are taken verbatim from projects/adrv9009/src/app/*.c.
Run against a board farm:
    HW_DAUGHTER=adrv9009 HW_CARRIER=zc706 \\
    pytest tests/hil --lg-env tests/hil/env/adrv9009_zc706.yaml \\
           -m iio_hardware -k boot_console --noos-xsa /path/adrv9009_zc706.xsa
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

# Failure markers from headless_arm.c / app_*.c — if any appears, fail fast.
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
    """Wait for `good`, failing immediately if any ERROR_MARKER appears first.

    Uses labgrid's pexpect-style expect with a pattern list; index 0 is the
    success pattern.
    """
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
