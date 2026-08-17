"""Phase 1 and Phase 2 HIL tests for AD9361 RF transceiver.

Run on hardware (local bench or labgrid farm):

    # Phase 1: Console boot test
    pytest tests/hil/tests/test_ad9361.py \
        --lg-env tests/hil/env/ad9361_zc706.yaml \
        -m iio_hardware --noos-project ad9361 --noos-build demo \
        --noos-xsa /path/ad9361_zc706.xsa

    # Phase 2: IIO / pyadi test
    pytest tests/hil/tests/test_ad9361.py \
        --lg-env tests/hil/env/ad9361_zc706.yaml \
        -m iio_hardware --noos-project ad9361 --noos-build iio \
        --noos-xsa /path/ad9361_zc706.xsa \
        --noos-iio-uri 'serial:/dev/ttyUSB0,115200'
"""

import pytest

pytestmark = [
    pytest.mark.iio_hardware(["ad9361"]),
    pytest.mark.iio_carrier(["zc706", "zed", "zcu102"]),
]

# Positive boot milestones for AD9361 firmware.
BOOT_BANNER = r"(ad9361_init|AD9361|ad9361)"
INIT_DONE = r"(successfully initialized|AD9361 Rev|Done|OK)"

# Failure markers from ad9361 initialization routines.
ERROR_MARKERS = [
    r"error: ad9361_init\(\) failed",
    r"ad9361_init.*error",
    r"axi_adc_init\(\) failed",
    r"axi_dac_init\(\) failed",
    r"axi_dmac_init\(\) failed",
    r"Altera Bridge Init Error!",
]


def _expect_or_error(console, good, timeout):
    """Wait for `good`, failing immediately if any ERROR_MARKER appears first."""
    index, before, _after, _match = console.expect([good] + ERROR_MARKERS, timeout=timeout)
    if index != 0:
        pytest.fail(f"firmware error before {good!r}: matched "
                    f"{ERROR_MARKERS[index - 1]!r}\n--- console ---\n{before}")
    return before


def test_boot_console_ad9361(loaded_firmware):
    """AD9361 firmware boots, initializes transceiver, and runs to completion."""
    console = loaded_firmware["console"]
    _expect_or_error(console, BOOT_BANNER, timeout=30)
    _expect_or_error(console, INIT_DONE, timeout=120)


@pytest.fixture
def iio_uri(request, loaded_firmware):
    """Resolve libiio URI for booted AD9361 IIOD firmware (or skip)."""
    uri = request.config.getoption("--noos-iio-uri")
    if not uri:
        pytest.skip("no --noos-iio-uri provided for Phase-2 IIO test")
    return uri


def test_iio_ad9361(iio_uri):
    """The IIOD context is reachable and exposes the ad9361-phy device."""
    iio = pytest.importorskip("iio", reason="libiio python bindings unavailable")
    ctx = iio.Context(iio_uri)
    names = [d.name for d in ctx.devices]
    assert any("ad9361-phy" in (n or "") for n in names), \
        f"ad9361-phy not found; devices={names}"


def test_pyadi_ad9361(iio_uri):
    """pyadi-iio can attach to AD9361 and query device properties."""
    adi = pytest.importorskip("adi", reason="pyadi-iio unavailable")
    dev = adi.ad9361(uri=iio_uri)
    assert dev.rx_sample_rate > 0
