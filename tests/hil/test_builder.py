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
