from __future__ import annotations

from core.sports.translator import loc as L

DRILL_VENUES = {
    "drill_film": ["venue_green_groomer"],
    "drill_land_stance": ["venue_dryland"],
    "drill_land_squat": ["venue_dryland"],
    "drill_wedge_stop": ["venue_green_groomer"],
    "drill_wedge_c": ["venue_green_groomer"],
    "drill_hip_steer": ["venue_green_groomer", "venue_dryland"],
    "drill_christie": ["venue_green_groomer", "venue_blue_groomer"],
    "drill_hands": ["venue_green_groomer", "venue_blue_groomer"],
    "drill_hockey": ["venue_green_groomer", "venue_blue_groomer"],
    "drill_skid_short": ["venue_blue_groomer"],
    "drill_one_ski": ["venue_green_groomer", "venue_blue_groomer"],
    "drill_carve_round": ["venue_blue_groomer"],
    "drill_carve_medium": ["venue_red_piste"],
    "drill_carve_short": ["venue_red_piste"],
    "drill_mogul_absorb": ["venue_mogul_field"],
    "drill_mogul_line": ["venue_mogul_field", "venue_black_steep"],
    "drill_sideslip": ["venue_green_groomer", "venue_blue_groomer"],
    "drill_flex_extend": ["venue_blue_groomer"],
    "drill_firm_edge": ["venue_blue_groomer", "venue_red_piste"],
    "drill_steep_pivot": ["venue_black_steep"],
    "drill_powder_bounce": ["venue_offpiste"],
}

TERRAIN_VENUES = {
    "green": ["venue_green_groomer"],
    "blue": ["venue_blue_groomer"],
    "red": ["venue_red_piste"],
    "black": ["venue_black_steep", "venue_mogul_field"],
    "park": ["venue_park"],
    "mogul": ["venue_mogul_field"],
    "offpiste": ["venue_offpiste"],
    "any": ["venue_green_groomer", "venue_blue_groomer", "venue_red_piste"],
}


def terrains() -> dict:
    return {
        "green": {"id": "green", "name": L("Green run"), "desc": L("Suggested green run; slope is not measured.")},
        "blue": {"id": "blue", "name": L("Blue run"), "desc": L("Suggested blue run; slope is not measured.")},
        "red": {"id": "red", "name": L("Red (steep groomed) run"), "desc": L("Suggested red run; slope is not measured.")},
        "black": {"id": "black", "name": L("Black run"), "desc": L("Suggested black run; slope is not measured.")},
        "park": {"id": "park", "name": L("Park"), "desc": L("Suggested park terrain; this app does not score air.")},
        "mogul": {"id": "mogul", "name": L("Mogul"), "desc": L("Suggested mogul field; bump shape is not measured.")},
        "offpiste": {
            "id": "offpiste",
            "name": L("Off-piste (inside the resort boundary)"),
            "desc": L("Suggested off-piste inside the resort boundary; snow depth is not measured."),
        },
        "any": {
            "id": "any",
            "name": L("Any terrain"),
            "desc": L("No terrain suggestion at this stage; use the runs you already ski well."),
        },
    }


def venues() -> dict:
    return {
        "venue_green_groomer": {
            "id": "venue_green_groomer",
            "terrain": "green",
            "name": L("Green run"),
            "desc": L("Quiet, easy green run — master the wedge stop first."),
            "tips": L("Pick the gentlest pitch; avoid ice and crowded runouts."),
        },
        "venue_blue_groomer": {
            "id": "venue_blue_groomer",
            "terrain": "blue",
            "name": L("Blue run"),
            "desc": L("Moderate groomed blue run; for parallel, skids, and long-radius carve."),
            "tips": L("Prefer fewer people and softer snow; shallower turns on ice."),
        },
        "venue_red_piste": {
            "id": "venue_red_piste",
            "terrain": "red",
            "name": L("Red (steep groomed) run"),
            "desc": L("Steeper groomed red run; for medium and short carve heuristics."),
            "tips": L("Practice inclination on blue before moving to red; drop to an easier pitch when form fades."),
        },
        "venue_black_steep": {
            "id": "venue_black_steep",
            "terrain": "black",
            "name": L("Black steep"),
            "desc": L("Steep/hard suggestion for fall-line moguls only; still not measured."),
            "tips": L("Round bumps, an open line, visible troughs; do not force a black run."),
        },
        "venue_mogul_field": {
            "id": "venue_mogul_field",
            "terrain": "mogul",
            "name": L("Mogul field"),
            "desc": L("Round, shallow bumps; absorb in a straight line first."),
            "tips": L("Avoid sharp bumps, jumps, and a too-narrow line."),
        },
        "venue_park": {
            "id": "venue_park",
            "terrain": "park",
            "name": L("Park"),
            "desc": L("Display only: boxes, rails, and jumps with a coach; the app does not score them."),
            "tips": L("Only try boxes, rails, or jumps with a coach, a helmet, and a supervised park."),
        },
        "venue_offpiste": {
            "id": "venue_offpiste",
            "terrain": "offpiste",
            "name": L("Off-piste (inside the resort boundary)"),
            "desc": L("Soft, ungroomed snow just off a marked run; stay inside the resort boundary."),
            "tips": L("Never ski off-piste alone; avoid avalanche terrain and sidecountry, and keep a partner in sight."),
        },
        "venue_dryland": {
            "id": "venue_dryland",
            "terrain": "green",
            "name": L("Dryland / flat"),
            "desc": L("Indoors or flat ground for stance and single-leg strength."),
            "tips": L("Non-slip floor; a handhold nearby helps."),
        },
    }


def categories() -> dict:
    return {
        "alpine_piste": L("Groomed-run recreational alpine"),
        "alpine_moguls": L("Mogul skiing"),
        "alpine_offpiste": L("Off-piste and soft snow"),
        "park": L("Park / jumps"),
        "alpine_race": L("Race gates"),
        "alpine_switch": L("Switch alpine"),
    }
