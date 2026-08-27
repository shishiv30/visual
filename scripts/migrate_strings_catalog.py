"""One-shot: build locales/strings.json from zh_en + glossary (English keys, no en field)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = {
    "camera_title": "Camera device",
}
SUPPORTED = ("es", "zh", "ko", "ja", "fr", "de", "it", "pt")


def main() -> None:
    zh_en = json.loads((ROOT / "locales" / "zh_en.json").read_text(encoding="utf-8"))["ui"]
    glossary = json.loads(
        (ROOT / "content" / "ski" / "glossary.zh-en.json").read_text(encoding="utf-8")
    )

    strings: dict[str, dict[str, str]] = {}
    snake_to_en: dict[str, str] = {}

    for snake, pair in zh_en.items():
        en = OVERRIDES.get(snake, pair["en"])
        zh = pair["zh"]
        if en in strings and strings[en].get("zh") != zh:
            raise SystemExit(f"collision {en!r}: {strings[en]} vs {zh} for {snake}")
        if en not in strings:
            strings[en] = {"zh": zh}
        snake_to_en[snake] = en

    for lang in SUPPORTED:
        path = ROOT / "locales" / f"{lang}.json"
        if not path.is_file():
            continue
        flat = json.loads(path.read_text(encoding="utf-8"))
        for snake, text in flat.items():
            en_key = snake_to_en.get(snake)
            if not en_key:
                continue
            if lang == "zh":
                strings[en_key]["zh"] = str(text)
                continue
            old_en = zh_en.get(snake, {}).get("en")
            if str(text) == en_key or str(text) == old_en:
                continue
            strings[en_key][lang] = str(text)

    for zh, en in (glossary.get("phrases") or {}).items():
        en_s = str(en).strip()
        zh_s = str(zh).strip()
        if not en_s:
            continue
        if en_s not in strings:
            strings[en_s] = {"zh": zh_s}
        elif not strings[en_s].get("zh"):
            strings[en_s]["zh"] = zh_s

    for zh, en in (glossary.get("terms") or {}).items():
        en_s = str(en).strip()
        zh_s = str(zh).strip()
        if en_s and en_s not in strings:
            strings[en_s] = {"zh": zh_s}

    extras = {
        " cm": {"zh": " cm"},
        " kg": {"zh": " kg"},
        "MM/dd/yyyy": {"zh": "yyyy/MM/dd"},
        "—": {"zh": "—"},
        "--": {"zh": "--"},
        "JPEG (*.jpg)": {"zh": "JPEG (*.jpg)"},
        "MP4 (*.mp4)": {"zh": "MP4 (*.mp4)"},
        "Unknown": {"zh": "未识别"},
        "Re-film": {"zh": "请重拍"},
        (
            "Stage cannot be judged when the shot is unstable, "
            "occluded, or out of curriculum scope."
        ): {"zh": "镜头不稳、遮挡或非本课程种类时不判定阶段。"},
    }
    for key, entry in extras.items():
        strings.setdefault(key, entry)

    missing_zh = [k for k, v in strings.items() if not str(v.get("zh", "")).strip()]
    if missing_zh:
        raise SystemExit(f"missing zh: {missing_zh[:20]}")

    for entry in strings.values():
        entry.pop("en", None)

    out = {
        "schema_version": "2.0.0",
        "strings": dict(sorted(strings.items(), key=lambda item: item[0].lower())),
    }
    (ROOT / "locales" / "strings.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "locales" / "_snake_to_en.json").write_text(
        json.dumps(snake_to_en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote strings.json ({len(strings)} keys), snake map ({len(snake_to_en)})")


if __name__ == "__main__":
    main()
