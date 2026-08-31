"""Skill tree: the whole progression with per-node state (design §8).

v2's ``_tree_path`` walked parents up from the current stage and then followed
``next_levels[0]`` forward — one line, no branches, and each node carried only
``{id, name, current}``. The user requirement is the opposite: show completed,
current *and* future stages, branches included, with catalog rungs greyed and
locked rungs explaining themselves.

So :func:`build_tree` emits a node for **every** level in the bundle — the piste
spine, the mogul branch, the off-piste branch and the four catalog park/race
rungs — with:

``state``          completed / current / available / locked / not_applicable
``score_best``     best stage score this athlete ever recorded on the rung
``gates_passed``   "3/5" from the same history
``locked_reason``  the prerequisite that is missing, named
``branch``         piste / moguls / offpiste / park / race
``depth``          longest-path layer, so a client can lay the graph out
``parents`` / ``children``

:func:`tree_path_projection` keeps the 2.1.0 ``tree_path`` alive as a projection
of the same graph, so a client that only understands 2.1.0 renders exactly what
it did before (design §10).

The one mapping choice worth naming: ``alpine_switch`` has no branch of its own
in §8's five-value list, and switch skiing belongs to the freestyle family, so
it is reported under ``park``.
"""

from __future__ import annotations

from typing import Callable

from core.sports.curriculum import Curriculum, LevelSpec
from core.sports.history import StageHistory
from core.sports.profile import AthleteContext
from schemas.stage_report import NodeState, TreeNode, TreeNodeV3

BRANCH_BY_CATEGORY = {
    "alpine_piste": "piste",
    "alpine_moguls": "moguls",
    "alpine_offpiste": "offpiste",
    "park": "park",
    "alpine_race": "race",
    "alpine_switch": "park",
}

#: English display keys for the locked / not-applicable reasons.
NEEDS_LEVEL = "Needs {name} first"
NEEDS_CHECKPOINT = "Needs the {name} checkpoint"
NOT_APPLICABLE_AGE = (
    "Carving needs body mass to bend the ski; not applicable below age 13."
)


def _name(resolve: Callable[[str], str] | None, level_id: str) -> str:
    return str(resolve(level_id)) if callable(resolve) else level_id


def parents_map(curriculum: Curriculum) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {lid: [] for lid in curriculum.levels}
    for lid, spec in curriculum.levels.items():
        for nid in spec.next_levels:
            if nid in out and lid not in out[nid]:
                out[nid].append(lid)
    return out


def depths(curriculum: Curriculum) -> dict[str, int]:
    """Longest-path depth per node, cycle-safe.

    Relaxation rather than a topological sort: the bundle is a DAG today, but a
    future content edit that introduced a cycle must not hang the report.
    """
    parents = parents_map(curriculum)
    depth = {lid: 0 for lid in curriculum.levels}
    for _ in range(len(depth) + 1):
        changed = False
        for lid, ups in parents.items():
            if not ups:
                continue
            best = max(depth[up] + 1 for up in ups if up in depth)
            if best > depth[lid]:
                depth[lid] = best
                changed = True
        if not changed:
            break
    return depth


def age_excluded(level: LevelSpec, age_band: str | None) -> bool:
    if not age_band:
        return False
    return any(
        note.id == age_band and note.status == "not_applicable"
        for note in level.profile_notes
    )


def _prerequisite_ancestors(current_id: str, curriculum: Curriculum) -> set[str]:
    """All transitive direct prerequisites of ``current_id``.

    If the current stage was detected, the athlete must have already mastered
    every stage on the path that leads here. These are marked INFERRED rather
    than AVAILABLE so the UI can show "predicted passed" copy.
    """
    seen: set[str] = set()
    queue = list((curriculum.levels.get(current_id) or _empty_level()).prerequisites.levels)
    while queue:
        lid = queue.pop()
        if lid in seen:
            continue
        seen.add(lid)
        level = curriculum.levels.get(lid)
        if level:
            queue.extend(level.prerequisites.levels)
    return seen


class _empty_level:
    prerequisites = type("P", (), {"levels": [], "checkpoints": []})()


def _locked_reason(
    level: LevelSpec,
    curriculum: Curriculum,
    history: StageHistory,
    lang: str,
    resolve: Callable[[str], str] | None,
) -> str:
    """Name the first missing prerequisite, or ``""`` when the rung is open."""
    from core.i18n import t

    passed = history.passed_levels()
    for lid in level.prerequisites.levels:
        if lid not in passed:
            return t(NEEDS_LEVEL, lang=lang, name=_name(resolve, lid))
    for cid in level.prerequisites.checkpoints:
        if cid in history.checkpoints_passed:
            continue
        spec = curriculum.checkpoints.get(cid)
        label = t(spec.name.en, lang=lang) if spec is not None else cid
        return t(NEEDS_CHECKPOINT, lang=lang, name=label)
    return ""


def build_tree(
    curriculum: Curriculum,
    current_id: str,
    history: StageHistory | None = None,
    athlete: AthleteContext | None = None,
    *,
    lang: str = "en",
    name_for: Callable[[str], str] | None = None,
) -> list[TreeNodeV3]:
    """Every rung of the progression, with this athlete's state on it."""
    from core.i18n import t

    hist = history or StageHistory()
    age_band = getattr(athlete, "age_band", None)
    layer = depths(curriculum)
    parents = parents_map(curriculum)
    passed = hist.passed_levels()
    inferred_ids = _prerequisite_ancestors(current_id, curriculum) - passed
    current_name = _name(name_for, current_id)
    order = list(curriculum.level_ids) + [
        lid for lid in curriculum.catalog_level_ids if lid in curriculum.levels
    ]
    order += [lid for lid in curriculum.levels if lid not in order]
    nodes: list[TreeNodeV3] = []
    for lid in order:
        level = curriculum.levels.get(lid)
        if level is None:
            continue
        locked_reason = ""
        inferred_reason = ""
        if age_excluded(level, age_band):
            state = NodeState.NOT_APPLICABLE
            locked_reason = t(NOT_APPLICABLE_AGE, lang=lang)
        elif lid == current_id:
            state = NodeState.CURRENT
        elif lid in passed:
            state = NodeState.COMPLETED
        elif lid in inferred_ids:
            state = NodeState.INFERRED
            level_name = _name(name_for, lid)
            inferred_reason = t(
                "Predicted passed based on {current} result",
                lang=lang,
                current=current_name,
            )
        else:
            locked_reason = _locked_reason(
                level, curriculum, hist, lang, name_for
            )
            state = NodeState.LOCKED if locked_reason else NodeState.AVAILABLE
        nodes.append(
            TreeNodeV3(
                id=lid,
                name=_name(name_for, lid),
                kb_stage=level.kb_stage,
                tier=level.tier or "full",
                branch=BRANCH_BY_CATEGORY.get(level.category_id, "piste"),
                state=state,
                score_best=hist.score_best(lid),
                gates_passed=hist.gates_label(lid),
                locked_reason=locked_reason,
                inferred_reason=inferred_reason,
                depth=layer.get(lid, 0),
                parents=list(parents.get(lid, [])),
                children=list(level.next_levels),
            )
        )
    return nodes


def tree_path_projection(
    curriculum: Curriculum,
    stage_id: str,
    name_for: Callable[[str], str] | None = None,
) -> list[TreeNode]:
    """The 2.1.0 ``tree_path``: parents up, then ``next_levels[0]`` forward.

    Kept byte-for-byte compatible with v2's ``assess._tree_path`` so a 2.1.0
    client renders the same spine it always did.
    """
    parent: dict[str, str] = {}
    for lid, spec in curriculum.levels.items():
        for nid in spec.next_levels:
            parent.setdefault(nid, lid)
    chain: list[str] = []
    cursor = stage_id
    seen: set[str] = set()
    while cursor and cursor not in seen:
        seen.add(cursor)
        chain.append(cursor)
        cursor = parent.get(cursor, "")
    chain.reverse()
    nodes: list[TreeNode] = []
    for lid in chain:
        spec = curriculum.levels.get(lid)
        if spec is None:
            continue
        nodes.append(
            TreeNode(
                id=lid,
                name=_name(name_for, lid),
                current=lid == stage_id,
            )
        )
    cursor = stage_id
    seen_future: set[str] = {node.id for node in nodes}
    while True:
        spec = curriculum.levels.get(cursor)
        if spec is None or not spec.next_levels:
            break
        nxt = spec.next_levels[0]
        if nxt in seen_future:
            break
        next_spec = curriculum.levels.get(nxt)
        if next_spec is None:
            break
        nodes.append(TreeNode(id=nxt, name=_name(name_for, nxt), current=False))
        seen_future.add(nxt)
        cursor = nxt
    return nodes
