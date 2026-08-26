import json

import core.i18n as i18n
from core.i18n import LOCALES_DIR, SUPPORTED, set_language, t


def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def test_locale_files_share_en_keys() -> None:
    en_keys = set(_load("en"))
    assert en_keys
    for lang in SUPPORTED:
        assert set(_load(lang)) == en_keys, lang


def test_default_refresh_is_english() -> None:
    set_language("en")
    assert t("refresh") == "Reanalyze"


def test_missing_key_falls_back_to_en() -> None:
    set_language("zh")
    i18n._catalog.pop("refresh", None)
    assert t("refresh") == "Reanalyze"
    set_language("zh")
