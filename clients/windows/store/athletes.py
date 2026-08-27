"""Reusable athlete profiles under %LOCALAPPDATA%/visual/athletes.json."""

from __future__ import annotations

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from clients.windows.store.prefs import prefs_path


class AthleteGender(str, Enum):
    UNSPECIFIED = "unspecified"
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class AthleteProfile(BaseModel):
    key: str
    name: str
    birthday: str = ""
    height_cm: float
    gender: AthleteGender = AthleteGender.UNSPECIFIED
    weight_kg: float
    ski_cm: float
    updated_at: str = ""


class AthleteStore(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    athletes: list[AthleteProfile] = Field(default_factory=list)


def athletes_path() -> Path:
    override = os.environ.get("VISUAL_ATHLETES")
    if override:
        return Path(override)
    return prefs_path().parent / "athletes.json"


def format_measure(value: float) -> str:
    rounded = round(float(value), 1)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.1f}"


def athlete_key(name: str, weight_kg: float, height_cm: float, ski_cm: float) -> str:
    cleaned = " ".join(str(name).strip().split())
    return (
        f"{cleaned}-{format_measure(weight_kg)}-"
        f"{format_measure(height_cm)}-{format_measure(ski_cm)}"
    )


def _load_store() -> AthleteStore:
    path = athletes_path()
    if not path.is_file():
        return AthleteStore()
    try:
        return AthleteStore.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return AthleteStore()


def _save_store(store: AthleteStore) -> None:
    path = athletes_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(store.model_dump_json(indent=2), encoding="utf-8")


def list_athletes() -> list[AthleteProfile]:
    athletes = list(_load_store().athletes)
    athletes.sort(key=lambda item: item.key.lower())
    return athletes


def get_by_key(key: str) -> AthleteProfile | None:
    want = key.strip()
    for item in _load_store().athletes:
        if item.key == want:
            return item
    return None


def upsert_athlete(
    *,
    name: str,
    weight_kg: float,
    height_cm: float,
    ski_cm: float,
    birthday: str = "",
    gender: AthleteGender | str = AthleteGender.UNSPECIFIED,
) -> AthleteProfile:
    cleaned = " ".join(str(name).strip().split())
    if not cleaned:
        raise ValueError("name required")
    if weight_kg <= 0 or height_cm <= 0 or ski_cm <= 0:
        raise ValueError("measures must be positive")
    key = athlete_key(cleaned, weight_kg, height_cm, ski_cm)
    gender_value = (
        gender
        if isinstance(gender, AthleteGender)
        else AthleteGender(str(gender))
    )
    profile = AthleteProfile(
        key=key,
        name=cleaned,
        birthday=str(birthday or "").strip(),
        height_cm=round(float(height_cm), 1),
        gender=gender_value,
        weight_kg=round(float(weight_kg), 1),
        ski_cm=round(float(ski_cm), 1),
        updated_at=datetime.now().astimezone().isoformat(),
    )
    store = _load_store()
    replaced = False
    next_rows: list[AthleteProfile] = []
    for item in store.athletes:
        if item.key == key:
            next_rows.append(profile)
            replaced = True
        else:
            next_rows.append(item)
    if not replaced:
        next_rows.append(profile)
    store.athletes = next_rows
    _save_store(store)
    return profile
