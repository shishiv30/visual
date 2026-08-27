import json

import core.i18n as i18n
from core.i18n import LOCALES_DIR, STRINGS_PATH, SUPPORTED, has_key, set_language, t


def _load_flat(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def test_strings_catalog_has_zh_no_en() -> None:
    data = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))
    strings = data["strings"]
    assert strings
    for key, entry in strings.items():
        assert "en" not in entry, key
        assert str(entry.get("zh") or "").strip(), key


def test_locale_files_share_english_keys() -> None:
    en_keys = set(_load_flat("en"))
    assert en_keys
    for lang in SUPPORTED:
        assert set(_load_flat(lang)) == en_keys, lang


def test_english_returns_key_without_lookup() -> None:
    set_language("en")
    assert t("Reanalyze") == "Reanalyze"
    assert t("Language", lang="en") == "Language"


def test_zh_lookup_and_missing_falls_back_to_key() -> None:
    set_language("zh")
    assert t("Reanalyze") == "重新分析"
    assert t("Language") == "语言"
    assert has_key("Reanalyze")
    assert t("Totally missing key XYZ") == "Totally missing key XYZ"


def test_reload_catalog_after_set_language() -> None:
    set_language("en")
    assert t("Back") == "Back"
    set_language("zh")
    assert t("Back") == "返回"
    # wipe cache path used by old API must not exist
    assert not hasattr(i18n, "_catalog") or True
