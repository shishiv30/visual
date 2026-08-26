from __future__ import annotations

import json
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

HOOK = Path(__file__).resolve().parents[1] / ".cursor" / "hooks" / "keep_translations.py"
_spec = spec_from_file_location("keep_translations", HOOK)
assert _spec is not None and _spec.loader is not None
keep = module_from_spec(_spec)
_spec.loader.exec_module(keep)


def test_find_gaps_clean_on_repo() -> None:
    assert keep.find_gaps() == []


def test_after_edit_reminds_on_glossary(tmp_path: Path) -> None:
    payload = {
        "hook_event_name": "afterFileEdit",
        "file_path": str(tmp_path / "content" / "ski" / "glossary.zh-en.json"),
    }
    out = keep.handle(payload)
    assert "glossary.zh-en.json" in out["additional_context"]
    assert "build_locales.py" in out["additional_context"]


def test_after_edit_ignores_unrelated() -> None:
    out = keep.handle(
        {
            "hook_event_name": "afterFileEdit",
            "file_path": "clients/windows/ui/theme.py",
        }
    )
    assert out == {}


def test_stop_followup_when_glossary_missing(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "content" / "ski").mkdir(parents=True)
    (tmp_path / "locales").mkdir()
    glossary = {"terms": {}, "phrases": {}}
    (tmp_path / "content" / "ski" / "glossary.zh-en.json").write_text(
        json.dumps(glossary), encoding="utf-8"
    )
    (tmp_path / "content" / "ski" / "curriculum.v2.json").write_text(
        json.dumps({"name": {"zh": "犁式直滑", "en": "Wedge glide"}}),
        encoding="utf-8",
    )
    ui = {"ok": {"zh": "确定", "en": "OK"}}
    (tmp_path / "locales" / "zh_en.json").write_text(
        json.dumps({"ui": ui}), encoding="utf-8"
    )
    (tmp_path / "locales" / "zh.json").write_text(
        json.dumps({"ok": "确定"}), encoding="utf-8"
    )
    (tmp_path / "locales" / "en.json").write_text(
        json.dumps({"ok": "OK"}), encoding="utf-8"
    )
    for name in ("de", "es", "fr", "it", "ja", "ko", "pt"):
        (tmp_path / "locales" / f"{name}.json").write_text(
            json.dumps({"ok": "OK"}), encoding="utf-8"
        )
    monkeypatch.setattr(keep, "ROOT", tmp_path)
    out = keep.handle({"hook_event_name": "stop"})
    assert "followup_message" in out
    assert "犁式直滑" in out["followup_message"]
