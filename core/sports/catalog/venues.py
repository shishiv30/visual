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
}

TERRAIN_VENUES = {
    "green": ["venue_green_groomer"],
    "blue": ["venue_blue_groomer"],
    "red": ["venue_red_piste"],
    "black": ["venue_black_steep", "venue_mogul_field"],
    "park": ["venue_park"],
    "mogul": ["venue_mogul_field"],
}


def terrains() -> dict:
    return {
        "green": {"id": "green", "name": L("绿道"), "desc": L("绿道建议场地，非坡度实测。")},
        "blue": {"id": "blue", "name": L("蓝道"), "desc": L("蓝道建议场地，非坡度实测。")},
        "red": {"id": "red", "name": L("红道"), "desc": L("红道建议场地，非坡度实测。")},
        "black": {"id": "black", "name": L("黑道"), "desc": L("黑道建议场地，非坡度实测。")},
        "park": {"id": "park", "name": L("公园"), "desc": L("公园建议场地，本 App 不评空中。")},
        "mogul": {"id": "mogul", "name": L("蘑菇"), "desc": L("蘑菇场地建议，非包型实测。")},
    }


def venues() -> dict:
    return {
        "venue_green_groomer": {
            "id": "venue_green_groomer",
            "terrain": "green",
            "name": L("绿道平整雪道"),
            "desc": L("空、缓、人少的绿道，先把刹车练稳。"),
            "tips": L("选最缓的坡，避开冰面和拥挤出口。"),
        },
        "venue_blue_groomer": {
            "id": "venue_blue_groomer",
            "terrain": "blue",
            "name": L("蓝道平整雪道"),
            "desc": L("中等坡平整道，适合平行、搓雪和大弯。"),
            "tips": L("人少、雪软一点更好；冰面减小弯深。"),
        },
        "venue_red_piste": {
            "id": "venue_red_piste",
            "terrain": "red",
            "name": L("红道平整雪道"),
            "desc": L("更陡的平整道，适合中小弯卡宾启发式。"),
            "tips": L("先在蓝道能倾再上红道；累了换缓坡。"),
        },
        "venue_black_steep": {
            "id": "venue_black_steep",
            "terrain": "black",
            "name": L("黑色陡坡"),
            "desc": L("仅在蘑菇落差线课使用的陡/难建议，仍非实测。"),
            "tips": L("包圆、线空、能看到沟；不要为了黑道硬上。"),
        },
        "venue_mogul_field": {
            "id": "venue_mogul_field",
            "terrain": "mogul",
            "name": L("蘑菇区"),
            "desc": L("圆而浅的包，先直滑吸收。"),
            "tips": L("避开尖包、跳台和过窄的线。"),
        },
        "venue_park": {
            "id": "venue_park",
            "terrain": "park",
            "name": L("公园"),
            "desc": L("目录课：箱杆跳台请线下教练，软件不打分。"),
            "tips": L("只在有教练和防护的公园区域尝试。"),
        },
        "venue_dryland": {
            "id": "venue_dryland",
            "terrain": "green",
            "name": L("陆地平坦场地"),
            "desc": L("室内或平地，练站姿和单腿力量。"),
            "tips": L("防滑地面，旁边有扶手更好。"),
        },
    }


def categories() -> dict:
    return {
        "alpine_piste": L("平整雪道大众滑行"),
        "alpine_moguls": L("蘑菇滑行"),
        "park": L("公园/跳台"),
        "alpine_race": L("竞技旗门"),
        "alpine_switch": L("正倒滑转换"),
    }
