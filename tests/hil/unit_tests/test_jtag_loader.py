import zipfile

import jtag_loader


def test_build_upload_argv_order_and_contents():
    argv = jtag_loader.build_upload_argv(
        xsct="xsct", ws="/ws", hw_path="/hw", hw_basename="design.xsa",
        elf="/build/app.elf", jtag_cable_id="cable1")
    assert argv[:4] == ["xsct", "-nodisp", str(jtag_loader.UTIL_TCL), "upload"]
    assert argv[4:7] == ["/ws", "/hw", "design.xsa"]   # ws hw_path hw_basename
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
