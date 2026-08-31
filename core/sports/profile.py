"""Athlete profile as an analysis input (design §2.3).

Pure and client-independent: this module imports nothing from ``clients/`` and
nothing from ``schemas/``, so the pipeline, the assessment layer and any future
client can all build an :class:`AthleteContext` from the profile snapshot that
``ClipMeta.athlete`` already stores.

Policy, taken verbatim from the curriculum adaptation policy (design §2.3): a
profile may change the normalization, the applicable threshold band, or the
guidance. **It may never silently lower a pass standard.** Where a gate is not
applicable to a band, the report says *not applicable at this age* rather than
awarding a pass. ``sex`` is used only for equipment-fit guidance and the
injury-risk note; it never changes a score.

Every field is optional. A missing or partial profile yields ``None`` values
and a false :attr:`AthleteContext.is_complete`, never an exception.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

AGE_3_6 = "age-3-6"
AGE_7_12 = "age-7-12"
AGE_13_17 = "age-13-17"
AGE_18_39 = "age-18-39"
AGE_40_59 = "age-40-59"
AGE_60PLUS = "age-60plus"

AGE_BANDS: tuple[str, ...] = (
    AGE_3_6,
    AGE_7_12,
    AGE_13_17,
    AGE_18_39,
    AGE_40_59,
    AGE_60PLUS,
)

SEX_FEMALE = "female"
SEX_MALE = "male"
SEX_OTHER = "other"
SEXES: tuple[str, ...] = (SEX_FEMALE, SEX_MALE, SEX_OTHER)

#: Anthropometric prior for leg length as a fraction of standing height.
LEG_LEN_FRACTION = 0.53
DAYS_PER_YEAR = 365.25


def age_band_for(age_years: float | None) -> str | None:
    """Band id for an age in years, or ``None`` when the age is unknown.

    Ages below the youngest documented band clamp up to ``age-3-6``; a negative
    or non-numeric age is treated as unknown.
    """
    age = _as_float(age_years)
    if age is None or age < 0.0:
        return None
    if age < 7.0:
        return AGE_3_6
    if age < 13.0:
        return AGE_7_12
    if age < 18.0:
        return AGE_13_17
    if age < 40.0:
        return AGE_18_39
    if age < 60.0:
        return AGE_40_59
    return AGE_60PLUS


def normalize_sex(value: object) -> str | None:
    """Map a stored gender value to ``female`` / ``male`` / ``other``.

    ``unspecified``, empty and unrecognized values become ``None``.
    """
    raw = getattr(value, "value", value)
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None
    text = text.rsplit(".", 1)[-1]
    return text if text in SEXES else None


@dataclass(frozen=True)
class AthleteContext:
    """Size, age and sex of the skier in the clip, in analysis units.

    Distances are metres and kilograms so the measurement layer never has to
    guess a unit. Derived quantities are properties, so they cannot drift out
    of sync with the inputs they come from.
    """

    age_years: float | None = None
    height_m: float | None = None
    mass_kg: float | None = None
    sex: str | None = None
    ski_cm: float | None = None

    @property
    def age_band(self) -> str | None:
        """Threshold-band id for this athlete, or ``None`` when age is unknown."""
        return age_band_for(self.age_years)

    @property
    def leg_len_m(self) -> float | None:
        """Anthropometric leg-length estimate. A prior only, never a measurement."""
        if self.height_m is None or self.height_m <= 0.0:
            return None
        return LEG_LEN_FRACTION * self.height_m

    @property
    def bmi(self) -> float | None:
        """Body-mass index. Equipment guidance only — never a score input."""
        if not self.height_m or not self.mass_kg or self.height_m <= 0.0:
            return None
        return self.mass_kg / (self.height_m * self.height_m)

    @property
    def ski_len_ratio(self) -> float | None:
        """Ski length over standing height, for the equipment chapter."""
        if not self.ski_cm or not self.height_m or self.height_m <= 0.0:
            return None
        return self.ski_cm / (self.height_m * 100.0)

    @property
    def is_complete(self) -> bool:
        """True when age, height and mass are all known.

        Those three are what normalization and band selection need. ``sex`` and
        ``ski_cm`` feed guidance only, so they do not gate completeness.
        """
        return (
            self.age_years is not None
            and self.height_m is not None
            and self.mass_kg is not None
        )

    def to_dict(self) -> dict:
        """JSON-ready block, derived values included for the report's benefit."""
        return {
            "age_years": self.age_years,
            "age_band": self.age_band,
            "height_m": self.height_m,
            "mass_kg": self.mass_kg,
            "sex": self.sex,
            "ski_cm": self.ski_cm,
            "leg_len_m": self.leg_len_m,
            "bmi": self.bmi,
            "ski_len_ratio": self.ski_len_ratio,
        }

    @classmethod
    def from_dict(cls, data: object) -> AthleteContext:
        """Rebuild from a block written by :meth:`to_dict`. Unknown keys ignored."""
        if not isinstance(data, dict):
            return cls()
        return cls(
            age_years=_positive(data.get("age_years"), allow_zero=True),
            height_m=_positive(data.get("height_m")),
            mass_kg=_positive(data.get("mass_kg")),
            sex=normalize_sex(data.get("sex")),
            ski_cm=_positive(data.get("ski_cm")),
        )

    @classmethod
    def from_profile_snapshot(
        cls,
        snapshot: object,
        clip_date: date | datetime | str | None = None,
    ) -> AthleteContext:
        """Build from a stored ``AthleteProfile`` snapshot.

        Accepts the dict shape that ``ClipMeta.athlete`` holds — ``birthday``,
        ``gender``, ``height_cm``, ``weight_kg``, ``ski_cm`` — without importing
        any client code. ``clip_date`` is the date the clip was recorded, used
        for the age; it defaults to today. Missing, partial and malformed
        snapshots return a context of all ``None`` rather than raising.
        """
        if not isinstance(snapshot, dict):
            return cls()
        height_cm = _positive(snapshot.get("height_cm"))
        return cls(
            age_years=_age_years(snapshot.get("birthday"), clip_date),
            height_m=None if height_cm is None else height_cm / 100.0,
            mass_kg=_positive(snapshot.get("weight_kg")),
            sex=normalize_sex(snapshot.get("gender")),
            ski_cm=_positive(snapshot.get("ski_cm")),
        )


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _positive(value: object, *, allow_zero: bool = False) -> float | None:
    out = _as_float(value)
    if out is None:
        return None
    if out < 0.0 or (out == 0.0 and not allow_zero):
        return None
    return out


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    head = text.replace("Z", "+00:00").split("T", 1)[0].split(" ", 1)[0]
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def _age_years(
    birthday: object, clip_date: date | datetime | str | None
) -> float | None:
    born = _as_date(birthday)
    if born is None:
        return None
    when = _as_date(clip_date) or date.today()
    days = (when - born).days
    if days < 0:
        return None
    return days / DAYS_PER_YEAR
