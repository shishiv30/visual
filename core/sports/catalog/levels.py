from __future__ import annotations

from core.sports.catalog.helpers import level


def levels() -> list[dict]:
    return [
        level(
            "pizza_glide",
            "Wedge glide",
            "Glide straight in a wedge and stop on purpose.",
            ["cp_pg_stance", "cp_pg_knee", "cp_pg_com", "cp_pg_valgus"],
            ["drill_wedge_stop", "drill_land_stance"],
        ),
        level(
            "pizza",
            "Wedge turns",
            "Shallow C-turns; hip internal rotation steers; the wedge stays.",
            [
                "cp_pz_stance",
                "cp_pz_hip_ir",
                "cp_pz_knee",
                "cp_pz_turn",
                "cp_pz_upper",
                "cp_pz_gaze",
            ],
            ["drill_wedge_c", "drill_hip_steer"],
        ),
        level(
            "wedge_christie",
            "Wedge christie",
            "Wedge to start, close the inside ski to finish.",
            ["cp_wc_openclose", "cp_wc_stance"],
            ["drill_christie", "drill_land_squat"],
        ),
        level(
            "parallel",
            "Parallel skiing",
            "Matched skis and separation. After passing, choose short skids or long-radius carve.",
            ["cp_par_stance", "cp_par_upper", "cp_par_com"],
            ["drill_hands", "drill_land_stance"],
        ),
        level(
            "skid_short",
            "Short skidded turns",
            "Short-radius skids for speed control; hockey stop required. Then moguls.",
            ["cp_sk_hockey", "cp_sk_rhythm", "cp_sk_knee", "cp_sk_hands"],
            ["drill_hockey", "drill_skid_short"],
        ),
        level(
            "carve_long",
            "Long-radius carve",
            "Heuristic inclination and parallel stance, not FIS. Learn one-ski first.",
            ["cp_cv_oneski", "cp_cv_parallel", "cp_cv_upper"],
            ["drill_one_ski", "drill_carve_round"],
        ),
        level(
            "carve_medium",
            "Medium-radius carve",
            "Shorten the radius only after long-radius inclination works.",
            ["cp_cv_oneski", "cp_cv_parallel", "cp_cvm_freq", "cp_cv_upper"],
            ["drill_carve_medium"],
        ),
        level(
            "carve_short",
            "Short-radius carve",
            "Fast edge change, quieter shoulders. End of the groomed carve branch.",
            ["cp_cv_oneski", "cp_cv_parallel", "cp_cvs_freq", "cp_cv_upper"],
            ["drill_carve_short"],
        ),
        level(
            "mogul_absorb",
            "Mogul absorption",
            "From the skid branch: absorb and stay on snow; do not jump.",
            ["cp_mg_amp", "cp_mg_quiet", "cp_mg_freq"],
            ["drill_mogul_absorb"],
        ),
        level(
            "mogul_fallline",
            "Mogul fall-line",
            "Linked absorption near the fall line. No air score.",
            ["cp_mg_amp", "cp_mg_quiet", "cp_mg_freq", "cp_mg_fall"],
            ["drill_mogul_line"],
        ),
        level(
            "ollie",
            "Ollie",
            "Display only: 2D pose does not score air or ski tips. Train with a coach.",
            [],
            [],
        ),
        level(
            "park",
            "Park skiing",
            "Display only: boxes, rails, and jumps are not scored.",
            [],
            [],
        ),
        level(
            "gates",
            "Race gates",
            "Display only: this app does not time gates.",
            [],
            [],
        ),
        level(
            "switch",
            "Switch alpine",
            "Display only: v2 video does not classify switch.",
            [],
            [],
        ),
    ]
