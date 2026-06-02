"""Xilinx bare-metal JTAG loader: xsct loads bitstream + ps7_init + .elf."""

from __future__ import annotations

import jtag_loader


class JTAGLoader:
    name = "jtag"

    def load(self, artifacts, target, options) -> None:
        import pytest
        xsa = options.get("xsa") or artifacts.xsa
        if not xsa:
            pytest.skip("jtag loader needs an .xsa (--noos-xsa) and none was found")
        elf = artifacts.require("elf")
        hw_path = artifacts.build_dir / "hil_hw"
        result = jtag_loader.upload(
            xsa=xsa,
            elf=elf,
            hw_path=hw_path,
            xsct=options.get("xsct") or "xsct",
            jtag_cable_id=options.get("jtag_cable") or "",
            remote_host=options.get("jtag_host"),
            remote_port=options.get("jtag_port"),
        )
        if result.returncode != 0:
            pytest.fail(f"JTAG upload failed (rc={result.returncode}):\n{result.stdout}")
