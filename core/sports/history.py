"""Per-athlete stage history: what this skier has already passed.

Design §8 wants the skill tree to say *completed* rather than *available*, and
§5 wants "previously passed levels raise adjacent levels" in the classifier
prior. Both need the same thing: a compact view over this athlete's earlier
reports.

The store owns the reports (``clients/windows/store/library.py``); ``core`` must
not import from ``clients``, so this module is duck-typed. Feed it
:class:`~schemas.stage_report.StageReport` objects, the dicts a stored report
parses into, or anything with the same attribute names. A missing or malformed
entry is skipped, never raised on: history is an optimisation of the report, not
a precondition for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


@dataclass(frozen=True)
class LevelHistory:
    """What is known about one level for one athlete."""

    level_id: str
    passed: bool = False
    score_best: float | None = None
    gates_passed: int = 0
    gates_total: int = 0
    clips: int = 0
    clip_id_best: str = ""


@dataclass
class StageHistory:
    """Every level this athlete has been assessed on."""

    levels: dict[str, LevelHistory] = field(default_factory=dict)
    checkpoints_passed: frozenset[str] = frozenset()

    @property
    def is_empty(self) -> bool:
        return not self.levels

    def passed_levels(self) -> frozenset[str]:
        return frozenset(
            lid for lid, item in self.levels.items() if item.passed
        )

    def best(self, level_id: str) -> LevelHistory | None:
        return self.levels.get(level_id)

    def score_best(self, level_id: str) -> float | None:
        item = self.levels.get(level_id)
        return None if item is None else item.score_best

    def gates_label(self, level_id: str) -> str:
        """``"3/5"`` for the tree, or ``""`` when this level was never assessed."""
        item = self.levels.get(level_id)
        if item is None or item.gates_total <= 0:
            return ""
        return f"{item.gates_passed}/{item.gates_total}"

    def clip_id_map(self) -> dict[str, str]:
        """``{level_id: clip_id}`` for every level that has a best clip recorded."""
        return {
            lid: lh.clip_id_best
            for lid, lh in self.levels.items()
            if lh.clip_id_best
        }

    @classmethod
    def from_reports(cls, reports: Iterable[Any] | None) -> StageHistory:
        """Fold a sequence of stored reports into a history.

        A level counts as *passed* when any earlier report on it said
        ``ready_for_next_stage``; the best stage score and the best gate tally
        are kept so the tree can show progress on a level that is not passed
        yet. Checkpoint ids are collected from passing keypoints so a level's
        ``prerequisites.checkpoints`` can be checked.
        """
        levels: dict[str, LevelHistory] = {}
        checkpoints: set[str] = set()
        for report in reports or ():
            level_id = str(_get(report, "stage_id") or "")
            if not level_id or level_id == "unknown":
                continue
            clip_id = str(_get(report, "clip_id") or "")
            ready = bool(_get(report, "ready_for_next_stage", False))
            try:
                score = float(_get(report, "score_0_100", 0.0) or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            gates_passed, gates_total = _gate_tally(report)
            for cid in _passed_checkpoint_ids(report):
                checkpoints.add(cid)
            prior = levels.get(level_id)
            if prior is None:
                levels[level_id] = LevelHistory(
                    level_id=level_id,
                    passed=ready,
                    score_best=score,
                    gates_passed=gates_passed,
                    gates_total=gates_total,
                    clips=1,
                    clip_id_best=clip_id,
                )
                continue
            prior_score = prior.score_best or 0.0
            levels[level_id] = LevelHistory(
                level_id=level_id,
                passed=prior.passed or ready,
                score_best=max(prior_score, score),
                gates_passed=max(prior.gates_passed, gates_passed),
                gates_total=max(prior.gates_total, gates_total),
                clips=prior.clips + 1,
                clip_id_best=clip_id if score >= prior_score else prior.clip_id_best,
            )
        return cls(levels=levels, checkpoints_passed=frozenset(checkpoints))


def _gate_tally(report: Any) -> tuple[int, int]:
    """``(passed, total)`` over the report's gate metrics, v2 fallback included."""
    metrics = _get(report, "metrics") or []
    gates = [m for m in metrics if bool(_get(m, "is_gate", False))]
    if gates:
        passed = sum(
            1
            for m in gates
            if str(_get(_get(m, "rubric"), "value", _get(m, "rubric")) or "")
            in ("pass", "strong")
        )
        return passed, len(gates)
    keypoints = _get(report, "keypoints") or []
    if not keypoints:
        return 0, 0
    passed = sum(1 for k in keypoints if _status(k) == "pass")
    return passed, len(keypoints)


def _status(keypoint: Any) -> str:
    raw = _get(keypoint, "status")
    return str(_get(raw, "value", raw) or "")


def _passed_checkpoint_ids(report: Any) -> list[str]:
    out: list[str] = []
    for keypoint in _get(report, "keypoints") or ():
        if _status(keypoint) == "pass":
            cid = str(_get(keypoint, "id") or "")
            if cid:
                out.append(cid)
    return out
