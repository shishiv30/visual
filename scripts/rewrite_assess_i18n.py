"""Rewrite assess.py to use t()/English keys for Localized projection."""

from __future__ import annotations

import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "core" / "sports" / "assess.py"


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    text = text.replace("from core.sports.translator import loc\n", "")
    if "from core.i18n import t\n" not in text:
        text = text.replace(
            "import core.i18n as i18n\n",
            "import core.i18n as i18n\nfrom core.i18n import t\n",
        )
    text = re.sub(
        r"def _loc\(zh: str, en: str, lang: str\) -> str:\n"
        r"    return zh if lang\.startswith\(\"zh\"\) else en\n\n\n"
        r"def _t\(zh: str, lang: str\) -> str:\n"
        r"    pair = loc\(zh\)\n"
        r"    return _loc\(pair\[\"zh\"\], pair\[\"en\"\], lang\)\n",
        (
            "def _text(item: object, lang: str) -> str:\n"
            '    """Resolve Localized or English key via i18n catalog."""\n'
            '    if hasattr(item, "en"):\n'
            '        return t(str(getattr(item, "en")), lang=lang)\n'
            "    return t(str(item), lang=lang)\n"
        ),
        text,
        count=1,
    )
    text = re.sub(
        r"_loc\(([^,\n]+)\.zh,\s*\1\.en,\s*([^)]+)\)",
        r"_text(\1, \2)",
        text,
    )
    text = text.replace("_t(", "_text(")
    text = text.replace('_text("未识别", lang)', '_text("Unknown", lang)')
    text = text.replace('_text("请重拍", lang)', '_text("Re-film", lang)')
    old_bad = (
        '_text(\n'
        '                    "镜头不稳、遮挡或非本课程种类时不判定阶段。",\n'
        "                    lang,\n"
        "                )"
    )
    new_bad = (
        "_text(\n"
        '                    "Stage cannot be judged when the shot is unstable, '
        'occluded, or out of curriculum scope.",\n'
        "                    lang,\n"
        "                )"
    )
    text = text.replace(old_bad, new_bad)
    if "_loc(" in text:
        raise SystemExit(f"remaining _loc calls:\n" + "\n".join(
            line for line in text.splitlines() if "_loc(" in line
        ))
    PATH.write_text(text, encoding="utf-8")
    print("rewrote", PATH)


if __name__ == "__main__":
    main()
