from __future__ import annotations

from core.sports.catalog.helpers import drill


def drills() -> list[dict]:
    return [
        drill(
            "drill_film",
            "How to film",
            "Stable follow-cam, one skier, side or rear-quarter.",
            [
                "Follow-cam; one alpine skier in frame.",
                "Side or rear-quarter, whole run, little occlusion.",
                "Keep the camera steady — shaky or wild motion prevents a reliable stage assessment.",
            ],
        ),
        drill(
            "drill_land_stance",
            "Athletic stance on land",
            "Soft ankles, knees, and hips; center of mass over mid-foot.",
            [
                "Standard: hip over ankle in profile; knees unlocked.",
                "3×30s; no collapsed backseat.",
            ],
        ),
        drill(
            "drill_land_squat",
            "Squats and split squats",
            "Single-leg strength for the christie close and carve outside ski.",
            [
                "Standard: knees track over the toes; pelvis level.",
                "3×8 squats; Bulgarian split squat 3×6 each side.",
            ],
        ),
        drill(
            "drill_wedge_stop",
            "Gentle-slope wedge brake",
            "Open the tails and edge to a stop; do not sit down.",
            [
                "Standard: ten stops, tips close, torso facing downhill.",
                "Wedge-glide on a green run, then open the tails and edge to a stop.",
            ],
        ),
        drill(
            "drill_wedge_c",
            "Shallow wedge C-turns",
            "Shallow C-turns while the wedge still brakes; load the outside ski.",
            [
                "Standard: linked S-track, no dart to the edge; the wedge stays through the turn.",
                "From a traverse, pressure the outside ski through a small C, then switch sides.",
            ],
        ),
        drill(
            "drill_hip_steer",
            "Hip internal-rotation steering",
            "Legs and hips steer; do not use the shoulders as a steering wheel.",
            [
                "Standard: the skis start to turn while the shoulders still face downhill.",
                "On land: athletic stance, rotate the femurs to turn the toes, keep the shoulders still.",
            ],
        ),
        drill(
            "drill_christie",
            "Close the inside ski",
            "Wedge to start, gradually match at the finish; do not snap shut.",
            [
                "Standard: stance narrows in the last third of the turn, still stable.",
                "Eight turns on green or blue; match the inside ski only in the last third of the turn.",
            ],
        ),
        drill(
            "drill_hands",
            "Low hands and pole rhythm",
            "Keep pole tips low and hands in front of the body, about waist to mid-torso, to time left–right turns.",
            [
                "Standard: on replay, the wrists stay below the shoulders.",
                "Easy slope, parallel or wedge: tap the downhill pole each turn.",
            ],
        ),
        drill(
            "drill_hockey",
            "Hockey stop",
            "Parallel-ski emergency stop; required braking skill before short skidded turns.",
            [
                "Standard: stop on a mark both ways; skis parallel, not in a wedge.",
                "From a gentle traverse, pivot both skis across the hill and set the edges to a stop.",
                "Eight each side; if speed builds, reset to a traverse before stopping.",
            ],
        ),
        drill(
            "drill_skid_short",
            "Short skidded-turn rhythm",
            "Linked short skids on parallel skis; mixed edge and skid is acceptable.",
            [
                "Standard: no long traverse between turns; knees flex and extend.",
                "Ten short turns on a blue run; quiet shoulders, hands low.",
            ],
        ),
        drill(
            "drill_one_ski",
            "One-ski / outside-leg drill",
            "Balance on the outside ski before carving.",
            [
                "Standard: glide on the outside ski; the inside ski taps the snow without taking weight.",
                "Six traverses per side; put the ski down if you wobble.",
            ],
        ),
        drill(
            "drill_carve_round",
            "Round long-radius turns",
            "Round, progressive long turns with parallel skis and inclination — coach heuristic, not a race carve score.",
            [
                "Standard: hips incline into the turn, shoulders quiet, stance parallel.",
                "Six large C-turns on a moderate pitch; longer outside leg.",
            ],
        ),
        drill(
            "drill_carve_medium",
            "Medium-radius edge change",
            "Shorten the radius only after long-radius inclination works.",
            [
                "Standard: a clear edge change, not an upright scrape.",
                "Eight medium turns on the same pitch; cadence between long and short.",
            ],
        ),
        drill(
            "drill_carve_short",
            "Short-radius carve cadence",
            "Faster edge changes without losing parallel inclination.",
            [
                "Standard: left-right symmetry, even quieter shoulders.",
                "Few high-quality sets; do not train fatigue into poor form.",
            ],
        ),
        drill(
            "drill_mogul_absorb",
            "Single-mogul absorption",
            "Shorten the legs at the crest, lengthen in the trough; stay on snow, do not jump.",
            [
                "Standard: quiet torso, large knee travel, no straight-leg slam.",
                "Eight straight lines over round, shallow bumps.",
            ],
        ),
        drill(
            "drill_mogul_line",
            "Trough fall-line rhythm",
            "Fewer traverses, linked absorption; still no air scoring.",
            [
                "Standard: hips stay near the fall line; the knees still do the work.",
                "Sets of 8–12 bumps; stop when form fades.",
            ],
        ),
    ]
