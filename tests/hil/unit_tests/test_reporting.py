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
