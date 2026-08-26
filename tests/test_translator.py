from __future__ import annotations

import json

from core.i18n import LOCALES_DIR
from core.sports.curriculum import CURRICULUM_PATH, load_curriculum
from core.sports.translator import GLOSSARY_PATH, en_for, loc, term_en


def _walk_zh(node: object, out: list[str]) -> None:
    if isinstance(node, dict):
        if "zh" in node and "en" in node and len(node) == 2:
            out.append(str(node["zh"]))
            return
        for value in node.values():
            _walk_zh(value, out)
        return
    if isinstance(node, list):
        for item in node:
            _walk_zh(item, out)


def test_term_glossary() -> None:
    assert term_en("犁式") == "wedge"
    assert term_en("卡宾") == "carve"
    assert term_en("冰球刹") == "hockey stop"
    assert term_en("蘑菇") == "mogul"


def test_phrase_lookup() -> None:
    pair = loc("冰球刹")
    assert pair["zh"] == "冰球刹"
    assert pair["en"] == "Hockey stop"
    assert en_for("平行式滑雪") == "Parallel skiing"


def test_curriculum_english_comes_from_glossary() -> None:
    data = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    phrases: list[str] = []
    _walk_zh(data, phrases)
    assert phrases
    for zh in phrases:
        assert en_for(zh)
    cur = load_curriculum()
    assert cur.levels["skid_short"].name.en == en_for("搓雪小弯滑雪")
    assert cur.drills["drill_hockey"].name.en == "Hockey stop"


def test_glossary_has_no_empty_english() -> None:
    data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    for zh, en in data["phrases"].items():
        assert zh.strip() and str(en).strip()
    for zh, en in data["terms"].items():
        assert zh.strip() and str(en).strip()


def test_ui_zh_en_dictionary_covers_locale_keys() -> None:
    dictionary = json.loads((LOCALES_DIR / "zh_en.json").read_text(encoding="utf-8"))["ui"]
    zh = json.loads((LOCALES_DIR / "zh.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    assert set(dictionary) == set(zh) == set(en)
    for key, pair in dictionary.items():
        assert zh[key] == pair["zh"]
        assert en[key] == pair["en"]
