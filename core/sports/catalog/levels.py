from __future__ import annotations

from core.sports.catalog.helpers import level


def levels() -> list[dict]:
    return [
        level(
            "pizza_glide",
            "犁式直滑",
            "用犁式板形直线下山并主动停下。",
            ["cp_pg_stance", "cp_pg_knee", "cp_pg_com", "cp_pg_valgus"],
            ["drill_wedge_stop", "drill_land_stance"],
        ),
        level(
            "pizza",
            "犁式转弯",
            "浅弧 C 弯，髋内旋导向，弯中保持犁。",
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
            "半犁式滑雪",
            "入弯犁、出弯收内侧板。",
            ["cp_wc_openclose", "cp_wc_stance"],
            ["drill_christie", "drill_land_squat"],
        ),
        level(
            "parallel",
            "平行式滑雪",
            "双板平行，上下分离。过关后可选搓雪或卡宾大弯。",
            ["cp_par_stance", "cp_par_upper", "cp_par_com"],
            ["drill_hands", "drill_land_stance"],
        ),
        level(
            "skid_short",
            "搓雪小弯滑雪",
            "短半径搓雪控速；必须掌握冰球刹。过关可进蘑菇。",
            ["cp_sk_hockey", "cp_sk_rhythm", "cp_sk_knee", "cp_sk_hands"],
            ["drill_hockey", "drill_skid_short"],
        ),
        level(
            "carve_long",
            "卡宾大弯滑行",
            "启发式内倾与平行，非 FIS。最好先掌握单脚滑。",
            ["cp_cv_oneski", "cp_cv_parallel", "cp_cv_upper"],
            ["drill_one_ski", "drill_carve_round"],
        ),
        level(
            "carve_medium",
            "卡宾中弯滑行",
            "在大弯能倾之后缩短半径。",
            ["cp_cv_oneski", "cp_cv_parallel", "cp_cvm_freq", "cp_cv_upper"],
            ["drill_carve_medium"],
        ),
        level(
            "carve_short",
            "卡宾小弯滑行",
            "快换刃，肩更静。平整道卡宾枝终点。",
            ["cp_cv_oneski", "cp_cv_parallel", "cp_cvs_freq", "cp_cv_upper"],
            ["drill_carve_short"],
        ),
        level(
            "mogul_absorb",
            "蘑菇滑行（吸收）",
            "从搓雪枝进入：先吸收贴雪，不要跳。",
            ["cp_mg_amp", "cp_mg_quiet", "cp_mg_freq"],
            ["drill_mogul_absorb"],
        ),
        level(
            "mogul_fallline",
            "蘑菇落差线",
            "少横切的连续吸收。不评空中。",
            ["cp_mg_amp", "cp_mg_quiet", "cp_mg_freq", "cp_mg_fall"],
            ["drill_mogul_line"],
        ),
        level(
            "ollie",
            "豚跳",
            "目录节点：2D 骨骼不评空中与板尖。请线下教练。",
            [],
            [],
        ),
        level(
            "park",
            "公园滑行",
            "目录节点：箱、杆、跳台不自动打分。",
            [],
            [],
        ),
        level(
            "gates",
            "竞技旗门",
            "目录节点：本 App 不做旗门计时。",
            [],
            [],
        ),
        level(
            "switch",
            "倒滑",
            "目录节点：v2 视频不自动判定倒滑。",
            [],
            [],
        ),
    ]
