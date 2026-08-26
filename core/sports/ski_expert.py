"""Ski expert acceptance of curriculum knowledge points and tree."""

from __future__ import annotations

from core.sports.curriculum import Curriculum, load_curriculum
from core.sports.knowledge import body_tokens, load_expert, load_signals, signal_ids
from core.sports.signals import CLIP_SIGNALS


def accept_curriculum(cur: Curriculum | None = None) -> list[str]:
    bundle = cur or load_curriculum()
    expert = load_expert()
    signals = load_signals()
    bodies = body_tokens()
    issues: list[str] = []

    if set(CLIP_SIGNALS) != set(signals):
        issues.append(
            f"signal catalog != runtime {sorted(set(CLIP_SIGNALS) ^ set(signals))}"
        )
    if abs(bundle.pass_score - float(expert["pass_score"])) > 1e-6:
        issues.append("pass_score != expert")
    if abs(bundle.checkpoint_pass - float(expert["checkpoint_pass"])) > 1e-6:
        issues.append("checkpoint_pass != expert")

    used_cps: set[str] = set()
    tree_next: dict = expert["tree_next"]
    level_terrain: dict = expert["level_terrain"]
    level_category: dict = expert["level_category"]
    required_on = expert["required_on_level"]
    heuristic_levels = set(expert["heuristic_levels"])
    catalog = set(expert["catalog_no_score"])
    proxy_cps = expert["proxy_checkpoints"]

    if set(tree_next) != set(bundle.levels):
        issues.append("expert tree ids != curriculum levels")

    for lid, level in bundle.levels.items():
        if lid not in tree_next:
            issues.append(f"level {lid} missing in expert tree")
            continue
        if list(level.next_levels) != list(tree_next[lid]):
            issues.append(f"{lid} next_levels {level.next_levels} != expert")
        want_t = level_terrain.get(lid)
        if want_t and level.terrain != want_t:
            issues.append(f"{lid} terrain {level.terrain} != {want_t}")
        want_c = level_category.get(lid)
        if want_c and level.category_id != want_c:
            issues.append(f"{lid} category {level.category_id} != {want_c}")
        if lid in catalog:
            if level.in_scope:
                issues.append(f"catalog {lid} still in_scope")
            if level.checkpoints:
                issues.append(f"catalog {lid} must not score checkpoints")
        else:
            if not level.in_scope:
                issues.append(f"scored {lid} marked out of scope")
            if not level.checkpoints:
                issues.append(f"scored {lid} has no checkpoints")
        if lid in heuristic_levels and not level.heuristic_not_fis_carve:
            issues.append(f"{lid} must be heuristic_not_fis_carve")
        if lid not in heuristic_levels and level.heuristic_not_fis_carve and lid not in catalog:
            if not lid.startswith("carve"):
                issues.append(f"{lid} unexpected heuristic flag")
        for cid in required_on.get(lid, []):
            if cid not in level.checkpoints:
                issues.append(f"{lid} missing required {cid}")
            else:
                spec = bundle.checkpoints[cid]
                if not spec.required:
                    issues.append(f"{cid} must be required on {lid}")
        for cid in level.checkpoints:
            used_cps.add(cid)
            if cid not in bundle.checkpoints:
                issues.append(f"{lid} unknown checkpoint {cid}")
        for nid in level.next_levels:
            if nid not in bundle.levels:
                issues.append(f"{lid} unknown next {nid}")
        if level.terrain not in bundle.terrains:
            issues.append(f"{lid} unknown terrain")
        for vid in level.venue_ids:
            if vid not in bundle.venues:
                issues.append(f"{lid} unknown venue {vid}")
        for did in level.session_drills:
            if did not in bundle.drills:
                issues.append(f"{lid} unknown session drill {did}")

    for cid, spec in bundle.checkpoints.items():
        if spec.signal not in signal_ids():
            issues.append(f"{cid} unknown signal {spec.signal}")
            continue
        sig = signals[spec.signal]
        allowed = set(sig["body"])
        for token in spec.body:
            if token not in bodies:
                issues.append(f"{cid} unknown body {token}")
            elif token not in allowed:
                issues.append(f"{cid} body {token} not valid for {spec.signal}")
        if not spec.body:
            issues.append(f"{cid} empty body")
        if spec.threshold.op == "between" and spec.threshold.hi is None:
            issues.append(f"{cid} between without hi")
        if spec.threshold.op != "between" and spec.threshold.hi is not None:
            issues.append(f"{cid} hi only valid for between")
        for did in spec.drills:
            if did not in bundle.drills:
                issues.append(f"{cid} unknown drill {did}")
        if not spec.drills:
            issues.append(f"{cid} has no drills")
        if cid in proxy_cps and not signals[spec.signal].get("proxy"):
            issues.append(f"{cid} expert proxy but signal {spec.signal} is not")
        if cid == "cp_sk_hockey" and spec.signal != "knee_flex_amp":
            issues.append("hockey stop must use knee_flex_amp proxy")
        if cid == "cp_cv_oneski" and spec.signal != "inward_lean":
            issues.append("outside-leg must use inward_lean proxy")
        if cid not in used_cps:
            issues.append(f"orphan checkpoint {cid}")

    for did, drill in bundle.drills.items():
        if not drill.training:
            issues.append(f"{did} empty training")
        for vid in drill.venue_ids:
            if vid not in bundle.venues:
                issues.append(f"{did} unknown venue {vid}")
    if bundle.sys_drill not in bundle.drills:
        issues.append("sys_drill missing")

    for vid, venue in bundle.venues.items():
        if venue.terrain not in bundle.terrains:
            issues.append(f"{vid} terrain {venue.terrain}")

    scored = [lid for lid, lv in bundle.levels.items() if lv.in_scope]
    if bundle.level_ids != scored:
        issues.append("level_ids != in_scope levels order")
    return issues
