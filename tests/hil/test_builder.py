import zipfile

import pytest

import builder


def test_discover_artifacts_first_match(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "app.elf").write_bytes(b"elf")
    (tmp_path / "sub" / "BOOT.BIN").write_bytes(b"boot")
    arts = builder.discover_artifacts(tmp_path)
    assert arts.elf == tmp_path / "app.elf"
    assert arts.boot_bin == tmp_path / "sub" / "BOOT.BIN"
    assert arts.hex is None
    assert arts.build_dir == tmp_path


def test_require_raises_when_missing(tmp_path):
    arts = builder.discover_artifacts(tmp_path)
    with pytest.raises(FileNotFoundError):
        arts.require("elf")


def test_unpack_if_zip(tmp_path):
    z = tmp_path / "a.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("x.elf", "e")
    dest = tmp_path / "out"
    out = builder.unpack_if_zip(z, dest)
    assert out == dest
    assert (dest / "x.elf").exists()


def test_unpack_if_zip_passthrough_for_dir(tmp_path):
    assert builder.unpack_if_zip(tmp_path, tmp_path / "unused") == tmp_path


def test_require_unknown_field_raises_filenotfound(tmp_path):
    arts = builder.discover_artifacts(tmp_path)
    with pytest.raises(FileNotFoundError):
        arts.require("not_a_field")


def test_build_via_build_projects_argv(tmp_path, monkeypatch):
    calls = {}

    def fake_run(argv, cwd=None, check=None):
        calls["argv"] = argv
        calls["cwd"] = cwd
        calls["check"] = check
        return None

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    out = builder.build_via_build_projects(
        project="adrv9009", platform="xilinx", build_name="demo",
        builds_dir=tmp_path, export_dir=tmp_path / "e", log_dir=tmp_path / "l",
        python="python3", hardware="adrv9009_zc706")
    assert out == tmp_path
    argv = calls["argv"]
    assert argv[0] == "python3"
    assert str(builder.BUILD_PROJECTS) in argv
    assert "-project=adrv9009" in argv
    assert "-platform=xilinx" in argv
    assert "-build_name=demo" in argv
    assert "-hardware=adrv9009_zc706" in argv
    assert f"-builds_dir={tmp_path}" in argv
    assert calls["check"] is True


def test_build_via_build_projects_omits_empty_hardware(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(builder.subprocess, "run",
                        lambda argv, cwd=None, check=None: calls.setdefault("argv", argv))
    builder.build_via_build_projects(
        project="iio_demo", platform="xilinx", build_name="iio_zed",
        builds_dir=tmp_path, export_dir=tmp_path / "e", log_dir=tmp_path / "l")
    assert not any(a.startswith("-hardware=") for a in calls["argv"])


def test_build_via_cmake_argv(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(builder.subprocess, "run",
                        lambda argv, cwd=None, check=None: calls.append(argv))
    out = builder.build_via_cmake(
        project="adrv9009", preset="adrv9009_zc706",
        defconfig="adrv9009/project.conf", builds_dir=tmp_path,
        xsa="/tmp/zc706.xsa", jobs=8)
    assert out == tmp_path / "build-adrv9009_zc706"
    configure, build = calls
    assert configure[:3] == ["cmake", "-B", str(tmp_path / "build-adrv9009_zc706")]
    assert "--preset" in configure and "adrv9009_zc706" in configure
    assert "-DPROJECT_DEFCONFIG=adrv9009/project.conf" in configure
    assert "-DXSA_PATH=/tmp/zc706.xsa" in configure
    assert build[:2] == ["cmake", "--build"]
    assert build[-4:] == ["--target", "adrv9009", "-j", "8"]


def test_build_via_cmake_omits_xsa_when_absent(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(builder.subprocess, "run",
                        lambda argv, cwd=None, check=None: calls.append(argv))
    builder.build_via_cmake(
        project="adrv9009", preset="adrv9009_zc706",
        defconfig="adrv9009/project.conf", builds_dir=tmp_path)
    configure = calls[0]
    assert not any(a.startswith("-DXSA_PATH=") for a in configure)
    assert not any(a == "-j" for a in calls[1])
