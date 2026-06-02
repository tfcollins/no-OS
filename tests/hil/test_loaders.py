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
