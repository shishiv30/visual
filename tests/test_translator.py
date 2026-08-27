from __future__ import annotations

import json

from core.i18n import LOCALES_DIR, STRINGS_PATH, has_key, t
from core.sports.curriculum import CURRICULUM_PATH, load_curriculum
from core.sports.translator import GLOSSARY_PATH, en_for, loc, term_en


def _walk_en(node: object, out: list[str]) -> None:
    if isinstance(node, dict):
        if "zh" in node and "en" in node and len(node) == 2:
            out.append(str(node["en"]))
            return
        for value in node.values():
            _walk_en(value, out)
        return
    if isinstance(node, list):
        for item in node:
            _walk_en(item, out)


def test_term_glossary() -> None:
    assert term_en("犁式") == "wedge"
    assert term_en("卡宾") == "carve"
    assert term_en("冰球刹") == "hockey stop"
    assert term_en("蘑菇") == "mogul"


def test_phrase_lookup_english_key() -> None:
    pair = loc("Hockey stop")
    assert pair["en"] == "Hockey stop"
    assert pair["zh"] == t("Hockey stop", lang="zh")
    assert en_for("平行式滑雪") == "Parallel skiing"


def test_curriculum_english_keys_in_strings() -> None:
    data = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    keys: list[str] = []
    _walk_en(data, keys)
    assert keys
    for en in keys:
        assert has_key(en), en
        assert t(en, lang="zh").strip()
    cur = load_curriculum()
    assert cur.levels["skid_short"].name.en == "Short skidded turns"
    assert cur.drills["drill_hockey"].name.en == "Hockey stop"


def test_glossary_has_no_empty_english() -> None:
    data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    for zh, en in data["phrases"].items():
        assert zh.strip() and str(en).strip()
    for zh, en in data["terms"].items():
        assert zh.strip() and str(en).strip()


def test_strings_catalog_covers_flat_locales() -> None:
    strings = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))["strings"]
    zh = json.loads((LOCALES_DIR / "zh.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    assert set(strings) == set(zh) == set(en)
    for key, entry in strings.items():
        assert "en" not in entry
        assert zh[key] == entry["zh"]
        assert en[key] == key
