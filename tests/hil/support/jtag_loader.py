"""Bare-metal JTAG loader for no-OS Xilinx targets.

Thin wrapper around the repo's xsct script
``tools/scripts/platform/xilinx/util.tcl`` (``upload`` proc), which performs the
Zynq-7000 bring-up over JTAG: connect -> reset CPU -> fpga <bitstream> ->
ps7_init -> dow <elf> -> con. We reuse util.tcl rather than re-implement it.

Remote xsct (hardware server on a farm host) is selected via the
XSCT_REMOTE_HOST / XSCT_REMOTE_PORT environment variables, which util.tcl reads.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UTIL_TCL = REPO_ROOT / "tools" / "scripts" / "platform" / "xilinx" / "util.tcl"


def stage_hw_path(xsa_path, hw_path) -> str:
    """Assemble the directory util.tcl loads from an .xsa.

    Copies the .xsa into hw_path and extracts ps7_init.tcl and the bitstream
    (renamed to <stem>.bit, which is what util.tcl expects). Returns the xsa
    basename (util.tcl argv slot).
    """
    xsa_path = Path(xsa_path)
    hw_path = Path(hw_path)
    hw_path.mkdir(parents=True, exist_ok=True)

    staged_xsa = hw_path / xsa_path.name
    shutil.copyfile(xsa_path, staged_xsa)
    stem = xsa_path.stem

    with zipfile.ZipFile(xsa_path) as z:
        names = z.namelist()
        for cand in ("ps7_init.tcl", "psu_init.tcl"):
            if cand in names:
                (hw_path / cand).write_bytes(z.read(cand))
                break
        bits = [n for n in names if n.lower().endswith(".bit")]
        if bits:
            (hw_path / f"{stem}.bit").write_bytes(z.read(bits[0]))

    return staged_xsa.name


def build_upload_argv(*, xsct, ws, hw_path, hw_basename, elf,
                      jtag_cable_id="", target_cpu="0",
                      template="Empty Application(C)", fsbl="0") -> list:
    """Construct the exact xsct argv (mirrors tools/scripts/xilinx.mk).

    Positional order consumed by util.tcl:
      function ws hw_path hw(basename) binary target template fsbl jtagtarget
    """
    return [
        xsct, "-nodisp", str(UTIL_TCL), "upload",
        str(ws), str(hw_path), hw_basename,
        str(elf), str(target_cpu), template, str(fsbl), jtag_cable_id,
    ]


def upload(*, xsa, elf, hw_path, xsct="xsct", jtag_cable_id="",
           remote_host=None, remote_port=None, timeout=600) -> subprocess.CompletedProcess:
    """Stage the .xsa and run util.tcl upload to load+run the .elf."""
    hw_basename = stage_hw_path(xsa, hw_path)
    env = dict(os.environ)
    if remote_host and remote_port:
        env["XSCT_REMOTE_HOST"] = str(remote_host)
        env["XSCT_REMOTE_PORT"] = str(remote_port)
    argv = build_upload_argv(
        xsct=xsct, ws=hw_path, hw_path=hw_path, hw_basename=hw_basename,
        elf=elf, jtag_cable_id=jtag_cable_id)
    return subprocess.run(
        argv, env=env, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
