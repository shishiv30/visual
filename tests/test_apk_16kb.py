from __future__ import annotations

import io
import struct
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_apk_16kb.py"
_spec = spec_from_file_location("check_apk_16kb", SCRIPT)
assert _spec is not None and _spec.loader is not None
check = module_from_spec(_spec)
_spec.loader.exec_module(check)


def _elf64(p_align: int) -> bytes:
    ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    ehdr = ident + struct.pack(
        "<HHIQQQIHHHHHH",
        3,
        183,
        1,
        0,
        64,
        0,
        0,
        64,
        56,
        1,
        0,
        0,
        0,
    )
    phdr = struct.pack(
        "<IIQQQQQQ",
        1,
        5,
        0,
        0,
        0,
        0x1000,
        0x1000,
        p_align,
    )
    return ehdr + phdr


def test_pt_load_alignments_16kb() -> None:
    assert check.pt_load_alignments(_elf64(16384)) == [16384]


def test_pt_load_alignments_rejects_4kb() -> None:
    assert check.pt_load_alignments(_elf64(4096)) == [4096]


def test_check_apk_reports_unaligned(tmp_path: Path) -> None:
    apk = tmp_path / "bad.apk"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("lib/arm64-v8a/libfoo.so", _elf64(4096))
    apk.write_bytes(buf.getvalue())
    problems = check.check_apk(apk)
    assert problems
    assert "4096" in problems[0]
    assert str(check.MIN_ALIGN) in problems[0]


def test_check_apk_ok(tmp_path: Path) -> None:
    apk = tmp_path / "ok.apk"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("lib/arm64-v8a/libfoo.so", _elf64(16384))
        zf.writestr("lib/x86_64/libfoo.so", _elf64(16384))
    apk.write_bytes(buf.getvalue())
    assert check.check_apk(apk) == []


def test_check_apk_rejects_x86_64_unaligned(tmp_path: Path) -> None:
    apk = tmp_path / "mixed.apk"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("lib/arm64-v8a/libfoo.so", _elf64(16384))
        zf.writestr("lib/x86_64/libfoo.so", _elf64(4096))
    apk.write_bytes(buf.getvalue())
    problems = check.check_apk(apk)
    assert problems
    assert "x86_64" in problems[0]


def test_not_elf() -> None:
    with pytest.raises(ValueError, match="not an ELF"):
        check.pt_load_alignments(b"not-elf" + bytes(64))
