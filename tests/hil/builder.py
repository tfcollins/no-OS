"""Produce or locate no-OS boot artifacts for HIL tests.

build_projects.py's xilinx export ships BOOT.BIN + bootgen_sysfiles.tar.gz but
NOT the .elf, so build mode (Task 3) discovers over the builds_dir (where the
.elf lives), not just the export dir.
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_PROJECTS = REPO_ROOT / "tools" / "scripts" / "build_projects.py"

# Artifacts field -> glob pattern; first sorted match wins.
_ARTIFACT_PATTERNS = {
    "elf": "*.elf",
    "boot_bin": "BOOT.BIN",
    "hex": "*.hex",
    "uf2": "*.uf2",
    "bin": "*.bin",
    "xsa": "*.xsa",
}


@dataclasses.dataclass
class Artifacts:
    build_dir: Path
    elf: Path | None = None
    boot_bin: Path | None = None
    hex: Path | None = None
    uf2: Path | None = None
    bin: Path | None = None
    xsa: Path | None = None

    def require(self, field: str) -> Path:
        value = getattr(self, field, None)
        if value is None:
            raise FileNotFoundError(f"no {field} artifact found under {self.build_dir}")
        return value


def discover_artifacts(root) -> Artifacts:
    """Recursively find boot artifacts under root; first match per type wins."""
    root = Path(root)
    found = {}
    for field, pattern in _ARTIFACT_PATTERNS.items():
        matches = sorted(root.rglob(pattern))
        if matches:
            found[field] = matches[0]
    return Artifacts(build_dir=root, **found)


def unpack_if_zip(path, dest) -> Path:
    """If path is a .zip, extract into dest and return dest; else return path.

    Assumes a trusted archive (team-controlled CI artifacts); does not sanitize
    member paths beyond zipfile's built-in traversal protection.
    """
    path = Path(path)
    if path.suffix == ".zip":
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as z:
            z.extractall(dest)
        return dest
    return path
