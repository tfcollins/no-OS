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
