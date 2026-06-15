"""Produce or locate no-OS boot artifacts for HIL tests.

Two build paths are supported:

- build_via_cmake(): the CMake build (default). Runs `cmake --preset <preset>`
  + `cmake --build --target <project>`; the .elf lands under
  <build_dir>/build/. Xilinx BSP generation needs a hardware design, passed
  through as -DXSA_PATH.
- build_via_build_projects(): the legacy Makefile build, kept for projects not
  yet migrated to CMake. Its xilinx export ships BOOT.BIN +
  bootgen_sysfiles.tar.gz but NOT the .elf, so it discovers over the builds_dir
  (where the .elf lives), not just the export dir.
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


def build_via_build_projects(*, project, platform, build_name, builds_dir,
                             export_dir, log_dir, python=sys.executable,
                             hardware=None) -> Path:
    """Run build_projects.py for one named build. Returns the builds_dir Path.

    Raises subprocess.CalledProcessError on build failure (check=True). After
    this returns, call discover_artifacts(builds_dir) to locate the .elf and
    (for xilinx) the BOOT.BIN.
    """
    builds_dir = Path(builds_dir)
    argv = [
        python, str(BUILD_PROJECTS), str(REPO_ROOT),
        f"-export_dir={export_dir}", f"-log_dir={log_dir}",
        f"-builds_dir={builds_dir}", f"-project={project}",
        f"-platform={platform}", f"-build_name={build_name}",
    ]
    if hardware:
        argv.append(f"-hardware={hardware}")
    subprocess.run(argv, cwd=REPO_ROOT, check=True)
    return builds_dir


def build_via_cmake(*, project, preset, defconfig, builds_dir, xsa=None,
                    jobs=None, python=sys.executable) -> Path:
    """Configure + build one project with CMake. Returns the build dir Path.

    Mirrors tools/scripts/no_os_build.py's run_build (`cmake -B <dir> --preset
    <preset> -DPROJECT_DEFCONFIG=<defconfig>` then `cmake --build --target
    <project>`), with -DXSA_PATH added so the Xilinx BSP can be generated. The
    .elf is written under <build_dir>/build/; call discover_artifacts() on the
    returned dir afterwards. Raises subprocess.CalledProcessError on failure.

    `python` is accepted for symmetry with build_via_build_projects(); CMake is
    invoked directly, so it is unused here.
    """
    builds_dir = Path(builds_dir)
    build_dir = builds_dir / f"build-{preset}"

    configure_cmd = [
        "cmake", "-B", str(build_dir), "--preset", preset,
        f"-DPROJECT_DEFCONFIG={defconfig}",
    ]
    if xsa:
        configure_cmd.append(f"-DXSA_PATH={xsa}")
    subprocess.run(configure_cmd, cwd=REPO_ROOT, check=True)

    build_cmd = ["cmake", "--build", str(build_dir), "--target", project]
    if jobs:
        build_cmd.extend(["-j", str(jobs)])
    subprocess.run(build_cmd, cwd=REPO_ROOT, check=True)
    return build_dir
