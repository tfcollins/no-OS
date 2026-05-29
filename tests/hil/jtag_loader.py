"""Bare-metal JTAG loader for no-OS Xilinx targets.

Thin wrapper around the repo's existing xsct script
``tools/scripts/platform/xilinx/util.tcl`` (``upload`` proc), which performs
the Zynq-7000 bring-up sequence over JTAG:

    connect -> reset CPU -> fpga <bitstream> -> ps7_init -> dow <elf> -> con

We deliberately reuse ``util.tcl`` rather than re-implement the sequence (and
rather than the plugin's ``XilinxJTAGDriver``, which does not run ``ps7_init``
for Cortex-A9). labgrid only provides board reservation, power, serial console
and the JTAG cable id; the actual load is this script.

``util.tcl`` expects, inside its ``hw_path`` argument:
  * ``<name>.xsa``        (the hardware design; ``<name>`` = xsa stem)
  * ``<name>.bit``        (bitstream, extracted/renamed from the xsa)
  * ``ps7_init.tcl``      (PS init, extracted from the xsa)

Remote xsct (hardware server on the farm host) is selected by the
``XSCT_REMOTE_HOST`` / ``XSCT_REMOTE_PORT`` environment variables, which
``util.tcl upload`` reads directly.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UTIL_TCL = REPO_ROOT / "tools" / "scripts" / "platform" / "xilinx" / "util.tcl"


def stage_hw_path(xsa_path: os.PathLike | str, hw_path: os.PathLike | str) -> str:
    """Assemble the directory ``util.tcl`` loads from an .xsa.

    Copies the .xsa into ``hw_path`` and extracts ``ps7_init.tcl`` and the
    bitstream (renamed to ``<stem>.bit``, which is what ``_write_pl`` expects).
    Returns the xsa basename (``util.tcl`` argv[3]).
    """
    xsa_path = Path(xsa_path)
    hw_path = Path(hw_path)
    hw_path.mkdir(parents=True, exist_ok=True)

    staged_xsa = hw_path / xsa_path.name
    shutil.copyfile(xsa_path, staged_xsa)
    stem = xsa_path.stem

    with zipfile.ZipFile(xsa_path) as z:
        names = z.namelist()
        # ps7_init.tcl (Zynq-7000) — util.tcl sources it at load time.
        for cand in ("ps7_init.tcl", "psu_init.tcl"):
            if cand in names:
                (hw_path / cand).write_bytes(z.read(cand))
                break
        # Bitstream -> <stem>.bit (util.tcl: fpga -file <hw_path>/<stem>.bit)
        bits = [n for n in names if n.lower().endswith(".bit")]
        if bits:
            (hw_path / f"{stem}.bit").write_bytes(z.read(bits[0]))

    return staged_xsa.name


def build_upload_argv(
    *,
    xsct: str,
    ws: os.PathLike | str,
    hw_path: os.PathLike | str,
    hw_basename: str,
    elf: os.PathLike | str,
    jtag_cable_id: str = "",
    target_cpu: str = "0",
    template: str = "Empty Application(C)",
    fsbl: str = "0",
) -> list[str]:
    """Construct the exact xsct argv (mirrors tools/scripts/xilinx.mk).

    Positional order consumed by util.tcl:
      function ws hw_path hw(basename) binary target template fsbl jtagtarget
    For Cortex-A9 no FSBL is needed (``util.tcl`` runs ps7_init directly), so
    ``fsbl`` is a placeholder.
    """
    return [
        xsct, "-nodisp", str(UTIL_TCL), "upload",
        str(ws), str(hw_path), hw_basename,
        str(elf), str(target_cpu), template, str(fsbl), jtag_cable_id,
    ]


def upload(
    *,
    xsa: os.PathLike | str,
    elf: os.PathLike | str,
    hw_path: os.PathLike | str,
    xsct: str = "xsct",
    jtag_cable_id: str = "",
    remote_host: str | None = None,
    remote_port: str | int | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess:
    """Stage the .xsa and run ``util.tcl upload`` to load+run the .elf."""
    hw_basename = stage_hw_path(xsa, hw_path)
    env = dict(os.environ)
    if remote_host and remote_port:
        env["XSCT_REMOTE_HOST"] = str(remote_host)
        env["XSCT_REMOTE_PORT"] = str(remote_port)
    argv = build_upload_argv(
        xsct=xsct, ws=hw_path, hw_path=hw_path, hw_basename=hw_basename,
        elf=elf, jtag_cable_id=jtag_cable_id,
    )
    return subprocess.run(
        argv, env=env, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
