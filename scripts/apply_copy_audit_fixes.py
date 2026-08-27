"""Apply coach/translator string renames and zh fixes to locales/strings.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "locales" / "strings.json"

# Old English key -> (new English key, zh). If new key == old, zh-only update.
RENAMES: dict[str, tuple[str, str]] = {
    "Knees over the toes; avoid a collapsed A-frame.": (
        "Knees track over the toes; don't let the knees collapse inward.",
        "膝沿脚尖方向；不要让膝盖向内塌。",
    ),
    "Heuristic: knees inside the ankles; steer with the legs.": (
        "Heuristic: steer with the legs — rotate the femurs so the ski tips turn while the torso stays quiet.",
        "经验提示：用腿转向——髋内旋带动板头转向，上身保持安静。",
    ),
    "About hip width; too wide is leftover wedge.": (
        "About hip-width; wider usually means you're still in a wedge.",
        "站距约髋宽；过宽说明犁式没收干净。",
    ),
    "Skidded turns require a matched-ski stop; knee-flex amplitude is the proxy.": (
        "Show you can stop on command with parallel skis (both directions).",
        "展示能用平行板按指令急停（左右两侧）。",
    ),
    "Do not straight-leg the snow.": (
        "Don't land or absorb with locked, straight legs.",
        "不要用锁死的直腿落地或缓冲。",
    ),
    "Outside-leg / one-ski": (
        "Inclination into the turn",
        "向弯心内倾",
    ),
    "Inclination heuristic: shoulders inside the hips toward the turn. Not a FIS edge angle.": (
        "Tip the body into the turn (hips inside the arc). Heuristic only — not a measured edge angle or FIS score.",
        "向弯心倾斜身体（髋在弧内）。仅为经验估分——非实测刃角或 FIS 得分。",
    ),
    "Throwing the shoulders wrecks the inclination geometry.": (
        "Throwing the shoulders wrecks inclination.",
        "甩肩会破坏内倾。",
    ),
    "Absorption amplitude": (
        "Knee absorption travel",
        "缓冲幅度",
    ),
    "Weak proxy: hip sway versus vertical travel.": (
        "Link bumps near the fall line with less traversing.",
        "少横切，沿落差线连贯过包。",
    ),
    "Knee cadence matches the bumps.": (
        "Knee flex cadence matches the bumps.",
        "膝屈伸节奏与雪包合拍。",
    ),
    "Avoid wild camera motion or the stage cannot be judged.": (
        "Keep the camera steady — shaky or wild motion prevents a reliable stage assessment.",
        "保持镜头稳定——剧烈晃动会导致阶段无法可靠判定。",
    ),
    "Eight turns on green or blue; close the ski only at the finish.": (
        "Eight turns on green or blue; match the inside ski only in the last third of the turn.",
        "绿/蓝道做 8 个弯，只在出弯后三分之一并内侧板。",
    ),
    "Pole tips low; hands in the lower visual field for left-right timing.": (
        "Keep pole tips low and hands in front of the body, about waist to mid-torso, to time left–right turns.",
        "杖尖放低，手在身前约腰至胸中，给左右转弯节拍。",
    ),
    "Matched-ski sideslip stop; required braking for short skidded turns.": (
        "Parallel-ski emergency stop; required braking skill before short skidded turns.",
        "平行板急停；进入搓雪小弯前的必过刹车技能。",
    ),
    "From a green-run traverse, plant, match both skis, and edge to a stop.": (
        "From a gentle traverse, pivot both skis across the hill and set the edges to a stop.",
        "从缓坡斜滑降开始，双板同时横切并立刃停下。",
    ),
    "Own one-legged balance before carving.": (
        "Balance on the outside ski before carving.",
        "刻滑前先能把重量放在外侧板上。",
    ),
    "Round the turn so the ski can bend (heuristic, not FIS).": (
        "Round, progressive long turns with parallel skis and inclination — coach heuristic, not a race carve score.",
        "平行板内倾做圆顺大弯——教练经验估分，非竞速刻滑得分。",
    ),
    "Shorten at the crest, lengthen in the trough; stay on snow, do not jump.": (
        "Shorten the legs at the crest, lengthen in the trough; stay on snow, do not jump.",
        "包顶缩短腿、沟底伸长；腿贴雪，不要跳。",
    ),
    "Ten short turns on a blue groomer; quiet shoulders, hands low.": (
        "Ten short turns on a blue run; quiet shoulders, hands low.",
        "蓝道平整处 10 个短弯一组，肩静手低。",
    ),
    "Green groomer": ("Green run", "绿道"),
    "Blue groomer": ("Blue run", "蓝道"),
    "Quiet, easy green groomer; own the brake first.": (
        "Quiet, easy green run — master the wedge stop first.",
        "安静缓坡绿道——先掌握犁式制动。",
    ),
    "Moderate groomed blue; for parallel, skids, and long-radius carve.": (
        "Moderate groomed blue run; for parallel, skids, and long-radius carve.",
        "中等平整蓝道；适合平行、搓雪与大弯刻滑。",
    ),
    "Red piste": ("Red (steep groomed) run", "红道（较陡平整道）"),
    "Steeper groomed red; for medium and short carve heuristics.": (
        "Steeper groomed red run; for medium and short carve heuristics.",
        "更陡的平整红道；适合中小弯刻滑经验课。",
    ),
    "Incline on blue before red; move easier when form fades.": (
        "Practice inclination on blue before moving to red; drop to an easier pitch when form fades.",
        "先在蓝道练内倾再上红道；动作变形时降到更缓的坡。",
    ),
    "Catalog: boxes, rails, and jumps with a coach; the app does not score them.": (
        "Display only: boxes, rails, and jumps with a coach; the app does not score them.",
        "仅目录展示：箱、杆、跳台需教练指导；本 App 不评分。",
    ),
    "Only try park features with a coach and protection.": (
        "Only try boxes, rails, or jumps with a coach, a helmet, and a supervised park.",
        "只在有教练、戴头盔且受监管的公园尝试箱、杆或跳台。",
    ),
    "Switch / fakie alpine": ("Switch alpine", "倒滑双板"),
    "Switch / fakie": ("Switch alpine", "倒滑双板"),
    "Catalog only: 2D pose does not score air or ski tips. Train with a coach.": (
        "Display only: 2D pose does not score air or ski tips. Train with a coach.",
        "仅目录展示：2D 骨骼不评空中与板尖。请线下教练。",
    ),
    "Catalog only: boxes, rails, and jumps are not scored.": (
        "Display only: boxes, rails, and jumps are not scored.",
        "仅目录展示：箱、杆、跳台不自动打分。",
    ),
    "Catalog only: this app does not time gates.": (
        "Display only: this app does not time gates.",
        "仅目录展示：本 App 不做旗门计时。",
    ),
    "Catalog only: v2 video does not classify switch.": (
        "Display only: v2 video does not classify switch.",
        "仅目录展示：v2 视频不自动判定倒滑。",
    ),
    "Green": ("Green run", "绿道"),
    "Blue": ("Blue run", "蓝道"),
    "Red": ("Red (steep groomed) run", "红道（较陡平整道）"),
    "Black": ("Black run", "黑道"),
    "Suggested green terrain; slope is not measured.": (
        "Suggested green run; slope is not measured.",
        "建议绿道；坡度未经实测。",
    ),
    "Suggested blue terrain; slope is not measured.": (
        "Suggested blue run; slope is not measured.",
        "建议蓝道；坡度未经实测。",
    ),
    "Suggested red terrain; slope is not measured.": (
        "Suggested red run; slope is not measured.",
        "建议红道；坡度未经实测。",
    ),
    "Suggested black terrain; slope is not measured.": (
        "Suggested black run; slope is not measured.",
        "建议黑道；坡度未经实测。",
    ),
}

# Zh-only patches (English key unchanged)
ZH_ONLY: dict[str, str] = {
    "Standard: hips stay near the fall line; the knees still do the work.": (
        "标准：髋大致沿落差线，少横切；仍由膝屈伸做功。"
    ),
    "Open the tails and edge to a stop; do not sit down.": (
        "推开板尾并立刃急停；不要一屁股坐下。"
    ),
    "Single-leg strength for the christie close and carve outside ski.": (
        "练单腿力量，为半犁收板与刻滑外侧承重做准备。"
    ),
    "Carve points are heuristics, not FIS carving scores.": (
        "刻滑要点为经验估分，不是 FIS 刻滑得分。"
    ),
    "Mogul": "雪包",
    "Mogul skiing": "雪包滑行",
    "Mogul fall-line": "雪包落差线",
    "Mogul field": "雪包区",
    "Bump cadence": "雪包节奏",
    "Trough fall-line rhythm": "沟底落差线节奏",
    "Athlete info required": "需要运动员信息",
    "New profile": "新建档案",
    "Select the person": "选择运动员",
    "Saved profile": "已存档案",
    "Heuristic score (0-100, not FIS)": "经验评分（0-100，非 FIS）",
    "Coach report (heuristics)": "教练报告（经验估分）",
    "Done": "完成",
    "carve": "刻滑",
    "Carve parallel": "平行板刻滑",
    "Long-radius carve": "大弯刻滑",
    "Medium-radius carve": "中弯刻滑",
    "Short-radius carve": "小弯刻滑",
    "Short-radius carve cadence": "短半径刻滑节奏",
}


def _replace_terms(zh: str) -> str:
    zh = zh.replace("卡宾", "刻滑")
    zh = zh.replace("蘑菇", "雪包")
    zh = zh.replace("启发式", "经验估分")
    zh = zh.replace("目录节点", "仅目录展示")
    zh = zh.replace("目录课", "仅目录展示")
    # UI 人物 → 运动员/档案 (careful: 人物框 stays for person-box UI)
    zh = zh.replace("新建人物", "新建档案")
    zh = zh.replace("已存人物", "已存档案")
    zh = zh.replace("选择人物", "选择运动员")
    zh = zh.replace("需要人物信息", "需要运动员信息")
    zh = zh.replace("或选择已存人物", "或选择已存档案")
    return zh


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    strings: dict[str, dict[str, str]] = data["strings"]

    for old, (new, zh) in RENAMES.items():
        entry = strings.pop(old, None) or {}
        entry = {k: v for k, v in entry.items() if k != "en"}
        entry["zh"] = zh
        if new in strings and new != old:
            # keep other langs from existing new if any
            merged = dict(strings[new])
            merged["zh"] = zh
            strings[new] = merged
        else:
            strings[new] = entry

    for key, zh in ZH_ONLY.items():
        if key not in strings:
            strings[key] = {"zh": zh}
        else:
            strings[key]["zh"] = zh

    for key, entry in list(strings.items()):
        zh = str(entry.get("zh") or "")
        fixed = _replace_terms(zh)
        if fixed != zh:
            entry["zh"] = fixed
        entry.pop("en", None)

    # Ensure new EN keys used only in catalog exist
    extras = {
        "Moderate groomed blue run; for parallel, skids, and long-radius carve.": (
            "中等平整蓝道；适合平行、搓雪与大弯刻滑。"
        ),
        "Steeper groomed red run; for medium and short carve heuristics.": (
            "更陡的平整红道；适合中小弯刻滑经验课。"
        ),
        "Suggested green run; slope is not measured.": "建议绿道；坡度未经实测。",
        "Suggested blue run; slope is not measured.": "建议蓝道；坡度未经实测。",
        "Suggested red run; slope is not measured.": "建议红道；坡度未经实测。",
        "Suggested black run; slope is not measured.": "建议黑道；坡度未经实测。",
        "Black run": "黑道",
        "Green run": "绿道",
        "Blue run": "蓝道",
        "Red (steep groomed) run": "红道（较陡平整道）",
        "Switch alpine": "倒滑双板",
        "Inclination into the turn": "向弯心内倾",
        "Knee absorption travel": "缓冲幅度",
    }
    for key, zh in extras.items():
        strings.setdefault(key, {"zh": zh})
        strings[key]["zh"] = zh

    data["strings"] = dict(sorted(strings.items(), key=lambda item: item[0].lower()))
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated strings.json ({len(data['strings'])} keys)")


if __name__ == "__main__":
    main()
