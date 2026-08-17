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
