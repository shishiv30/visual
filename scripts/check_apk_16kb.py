"""Fail if an APK's arm64-v8a .so files are not 16 KB page-aligned."""

from __future__ import annotations

import argparse
import struct
import sys
import zipfile
from pathlib import Path

PT_LOAD = 1
MIN_ALIGN = 16384
ELF_MAGIC = b"\x7fELF"


def pt_load_alignments(data: bytes) -> list[int]:
    if len(data) < 64 or not data.startswith(ELF_MAGIC):
        raise ValueError("not an ELF file")
    ei_class = data[4]
    if ei_class == 2:
        e_phoff = struct.unpack_from("<Q", data, 32)[0]
        e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
        align_off = 48
        align_fmt = "<Q"
    elif ei_class == 1:
        e_phoff = struct.unpack_from("<I", data, 28)[0]
        e_phentsize, e_phnum = struct.unpack_from("<HH", data, 42)
        align_off = 28
        align_fmt = "<I"
    else:
        raise ValueError(f"unsupported ELF class {ei_class}")
    aligns: list[int] = []
    for i in range(e_phnum):
        off = int(e_phoff) + i * e_phentsize
        if off + e_phentsize > len(data):
            raise ValueError("truncated program header")
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type != PT_LOAD:
            continue
        aligns.append(int(struct.unpack_from(align_fmt, data, off + align_off)[0]))
    if not aligns:
        raise ValueError("no PT_LOAD segments")
    return aligns


def check_apk(apk: Path) -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(apk) as zf:
        names = [n for n in zf.namelist() if n.startswith("lib/") and n.endswith(".so")]
        arm64 = [n for n in names if n.startswith("lib/arm64-v8a/")]
        if not arm64:
            return ["APK has no lib/arm64-v8a/*.so"]
        for name in names:
            data = zf.read(name)
            try:
                aligns = pt_load_alignments(data)
            except ValueError as exc:
                problems.append(f"{name}: {exc}")
                continue
            bad = [a for a in aligns if a < MIN_ALIGN]
            if bad:
                problems.append(f"{name}: PT_LOAD align {bad} < {MIN_ALIGN}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    args = parser.parse_args()
    apk: Path = args.apk
    if not apk.is_file():
        print(f"missing APK: {apk}", file=sys.stderr)
        return 2
    problems = check_apk(apk)
    if problems:
        print("16 KB alignment check FAILED:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"OK: all bundled .so PT_LOAD alignments >= {MIN_ALIGN} in {apk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
